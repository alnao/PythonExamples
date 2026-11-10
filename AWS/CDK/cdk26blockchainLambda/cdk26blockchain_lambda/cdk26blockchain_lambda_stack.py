"""Blockchain didattica con Lambda, DynamoDB e API Gateway REST, con una pagina web su CloudFront.

- tabella Blocks: un elemento per blocco (chiave chain="main" + index), cosi' l'ultimo blocco si legge con una query
- tabella Transactions: chiave sender + timestamp, indice StatusIndex per leggere le transazioni pending o mined
- una Lambda per ogni operazione (stesso codice in lambda/), ognuna con i soli permessi che le servono
- API Gateway REST con CORS e un limite di richieste (lo stage si chiama dev come nel CloudFormation)
- sito statico (web/) su S3 privato dietro CloudFront, con config.json che contiene l'URL delle API
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DIFFICULTY = 4  # zeri esadecimali iniziali dell'hash: in media 65.536 tentativi, meno di un secondo


class Cdk26BlockchainLambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name

        blocks = dynamodb.TableV2(self, "BlocksTable", table_name=f"{prefix}-Blocks",
            partition_key=dynamodb.Attribute(name="chain", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="index", type=dynamodb.AttributeType.NUMBER),
            billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)
        transactions = dynamodb.TableV2(self, "TransactionsTable", table_name=f"{prefix}-Transactions",
            partition_key=dynamodb.Attribute(name="sender", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            global_secondary_indexes=[dynamodb.GlobalSecondaryIndexPropsV2(
                index_name="StatusIndex",
                partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
                sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING))],
            billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)

        code = lambda_.Code.from_asset(os.path.join(ROOT, "lambda"), exclude=["__pycache__"])
        env = {"BLOCKS_TABLE": blocks.table_name, "TRANSACTIONS_TABLE": transactions.table_name,
               "DIFFICULTY": str(DIFFICULTY), "MAX_TX_PER_BLOCK": "50"}

        def function(name: str, handler: str, timeout: int = 10, memory: int = 256) -> lambda_.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{prefix}-{name}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            return lambda_.Function(self, name, function_name=f"{prefix}-{name}",
                runtime=lambda_.Runtime.PYTHON_3_13, architecture=lambda_.Architecture.ARM_64,
                handler=f"api.{handler}", code=code, environment=env, log_group=log_group,
                timeout=Duration.seconds(timeout), memory_size=memory)

        add_tx = function("AddTransaction", "add_transaction")
        # il mining usa la CPU: con piu' memoria Lambda da' piu' potenza (API Gateway chiude dopo 29 s)
        mine = function("MineBlock", "mine_block", timeout=28, memory=512)
        get_txs = function("GetTransactions", "get_transactions")
        get_balances = function("GetBalances", "get_balances")
        get_blocks = function("GetBlocks", "get_blocks")
        validate = function("ValidateChain", "validate_chain")

        # permessi minimi per ogni funzione
        transactions.grant(add_tx, "dynamodb:PutItem")
        transactions.grant_read_write_data(mine)
        blocks.grant_read_write_data(mine)
        transactions.grant_read_data(get_txs)
        transactions.grant_read_data(get_balances)
        blocks.grant_read_data(get_blocks)
        blocks.grant_read_data(validate)

        api = apigw.RestApi(self, "Api", rest_api_name=f"{prefix}-api",
            description="API della blockchain didattica cdk26",
            default_cors_preflight_options=apigw.CorsOptions(allow_origins=apigw.Cors.ALL_ORIGINS,
                                                             allow_methods=["GET", "POST", "OPTIONS"]),
            # niente abusi: al massimo 10 richieste al secondo (picchi di 20)
            deploy_options=apigw.StageOptions(stage_name="dev", throttling_rate_limit=10, throttling_burst_limit=20))
        for path, method, fn in (("transaction", "POST", add_tx), ("mine", "POST", mine),
                                 ("transactions", "GET", get_txs), ("balances", "GET", get_balances),
                                 ("blocks", "GET", get_blocks), ("validate", "GET", validate)):
            api.root.add_resource(path).add_method(method, apigw.LambdaIntegration(fn))

        # Sito statico: bucket privato, CloudFront con Origin Access Control
        site = s3.Bucket(self, "SiteBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                         enforce_ssl=True, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        distribution = cloudfront.Distribution(self, "Distribution", comment=f"{prefix} sito",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS))
        s3deploy.BucketDeployment(self, "SiteDeployment", destination_bucket=site,
            sources=[s3deploy.Source.asset(os.path.join(ROOT, "web")),
                     s3deploy.Source.json_data("config.json", {"apiUrl": api.url})],
            distribution=distribution, distribution_paths=["/*"],
            log_group=logs.LogGroup(self, "SiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "BlocksTableName", value=blocks.table_name)
        CfnOutput(self, "TransactionsTableName", value=transactions.table_name)
