"""API REST CRUD su una tabella DynamoDB, con una Lambda per ogni operazione.

- tabella DynamoDB on-demand (chiave id), cancellata al destroy
- quattro Lambda Python 3.13 (ARM) con lo stesso codice (lambda/items.py), ognuna con i soli permessi
  che le servono: PutItem, GetItem/Scan, UpdateItem, DeleteItem
- API Gateway REST: POST e GET /items, GET PUT DELETE /items/{id}, stage dev con limite di richieste
- log group dello stack per ogni Lambda, 7 giorni
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk09DynamoApiCrudStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = dynamodb.TableV2(self, "ItemsTable", table_name=nome_risorsa(self, "Items"),
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            removal_policy=RemovalPolicy.DESTROY)  # esempio: al destroy si cancellano anche i dati

        code = _lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"])

        def function(name: str, handler: str, *actions: str) -> _lambda.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{nome_risorsa(self, name)}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            fn = _lambda.Function(self, name, function_name=nome_risorsa(self, name),
                runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
                handler=f"items.{handler}", code=code, environment={"TABLE_NAME": self.table.table_name},
                timeout=Duration.seconds(10), log_group=log_group)
            self.table.grant(fn, *actions)  # solo le azioni che servono a questa funzione
            return fn

        create_fn = function("CreateItem", "create", "dynamodb:PutItem")
        read_fn = function("ReadItem", "read", "dynamodb:GetItem", "dynamodb:Scan")
        update_fn = function("UpdateItem", "update", "dynamodb:UpdateItem")
        delete_fn = function("DeleteItem", "delete", "dynamodb:DeleteItem")

        self.api = apigw.RestApi(self, "ItemsApi", rest_api_name=nome_risorsa(self, "ItemsApi"),
            description="cdk09: CRUD degli item su DynamoDB",
            deploy_options=apigw.StageOptions(stage_name="dev", throttling_rate_limit=10, throttling_burst_limit=20))
        items = self.api.root.add_resource("items")
        items.add_method("POST", apigw.LambdaIntegration(create_fn))
        items.add_method("GET", apigw.LambdaIntegration(read_fn))
        item = items.add_resource("{id}")
        item.add_method("GET", apigw.LambdaIntegration(read_fn))
        item.add_method("PUT", apigw.LambdaIntegration(update_fn))
        item.add_method("DELETE", apigw.LambdaIntegration(delete_fn))

        CfnOutput(self, "ItemsUrl", value=self.api.url_for_path("/items"))
        CfnOutput(self, "TableName", value=self.table.table_name)
