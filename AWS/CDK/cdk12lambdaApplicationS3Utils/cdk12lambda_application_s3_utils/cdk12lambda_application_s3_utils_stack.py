"""Applicazione serverless di utility sui file S3: zip -> Excel -> CSV -> database, con API e pagina web.

Flusso dei file nel bucket (regole EventBridge sugli eventi "Object Created"):
- INPUT/*.zip (anche tar, tar.gz, tgz) -> Lambda Decompress -> file estratti in DEZIPPED/
- DEZIPPED/*.xlsx -> Lambda ConvertToCsv (openpyxl) -> CSV/<nome>.csv
- CSV/*.csv -> Lambda ProcessCsv -> righe nella tabella di Aurora MySQL (creata con le colonne del primo CSV)
  e una riga di log nella tabella DynamoDB <stack>-Log
- TOSENDSFTP/* -> Lambda SendSftp -> server SFTP (facoltativa: solo con -c sftp_host=...)
Altro:
- Lambda ScanS3 ogni giorno alle 01:00 UTC: elenco dei file del bucket nella tabella <stack>-Scan (nuovo=S/N)
- API REST (stage dev, CORS) con una Lambda per ogni GET: upload-zip, list-excel-files, download-excel-file,
  read-rds-data, read-dynamodb-data, list-new-files, find-file
- allarmi CloudWatch (errori di ProcessCsv e ReadRdsData, 5xx dell'API) su un topic SNS (email con -c alarm_email=...)
- pagina web (web/) su S3 privato dietro CloudFront, con l'URL delle API in config.js

Rispetto all'esempio CloudFormation (Esempio12):
- Aurora MySQL Serverless v2 con pausa a 0 ACU e Data API: le Lambda non stanno nella VPC, quindi niente VPC
  endpoint di Secrets Manager (circa 17 $/mese) e niente driver MySQL
- openpyxl al posto di pandas e paramiko nello stesso layer, creato da build_layer.sh senza Docker
- bucket privato (upload e download con URL prefirmati), DynamoDB on-demand, nessun log di esecuzione di API Gateway
  (richiederebbe il ruolo CloudWatch nelle impostazioni dell'account)
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_rds as rds,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
)
from constructs import Construct

from .naming import nome_risorsa

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FOLDERS = {"INPUT_FOLDER": "INPUT", "DEZIPPED_FOLDER": "DEZIPPED", "CSV_FOLDER": "CSV", "SFTP_FOLDER": "TOSENDSFTP"}
DB_NAME = "es12db"
DB_TABLE = "es12table"
API_ROUTES = ("upload-zip", "list-excel-files", "download-excel-file", "read-rds-data", "read-dynamodb-data",
              "list-new-files", "find-file")


class Cdk12LambdaApplicationS3UtilsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, layer_dir: str = os.path.join(ROOT, "layer"),
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name
        self.functions = {}

        # VPC e subnet del database: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 2)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_1 = subnet_parameter(self, "subnetid1", default_subnets[0], "subnet 1 del database")
        subnet_2 = subnet_parameter(self, "subnetid2", default_subnets[1], "subnet 2 del database, in un'altra zona")

        # ---- dati: bucket, tabelle DynamoDB, database ----
        self.bucket = s3.Bucket(self, "DataBucket",
            event_bridge_enabled=True, block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
            # la pagina web carica e scarica i file direttamente su S3 con gli URL prefirmati
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET], allowed_origins=["*"],
                              allowed_headers=["*"], max_age=3000)],
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)

        self.log_table = dynamodb.TableV2(self, "LogTable", table_name=nome_risorsa(self, "Log"),
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)
        self.scan_table = dynamodb.TableV2(self, "ScanTable", table_name=nome_risorsa(self, "Scan"),
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(index_name="nomeFile-index",
                    partition_key=dynamodb.Attribute(name="nomeFile", type=dynamodb.AttributeType.STRING)),
                dynamodb.GlobalSecondaryIndexPropsV2(index_name="nuovo-index",
                    partition_key=dynamodb.Attribute(name="nuovo", type=dynamodb.AttributeType.STRING)),
            ],
            billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)

        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id,
                                          availability_zones=[Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())],
                                          private_subnet_ids=[subnet_1, subnet_2])
        # nessuna regola in ingresso: le Lambda usano la Data API (HTTPS), non la rete della VPC
        db_sg = ec2.SecurityGroup(self, "DatabaseSecurityGroup", vpc=vpc, allow_all_outbound=False,
                                  description="cdk12: database raggiungibile solo con la Data API")
        self.cluster = rds.DatabaseCluster(self, "Database",
            engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_09_0),
            writer=rds.ClusterInstance.serverless_v2("writer"),
            serverless_v2_min_capacity=0, serverless_v2_max_capacity=2,
            serverless_v2_auto_pause_duration=Duration.minutes(5),  # in pausa si paga solo lo storage
            vpc=vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_sg], default_database_name=DB_NAME,
            credentials=rds.Credentials.from_generated_secret("admin", exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"),
            enable_data_api=True, storage_encrypted=True, backup=rds.BackupProps(retention=Duration.days(1)),
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False)

        # ---- Lambda ----
        self.layer = _lambda.LayerVersion(self, "Libraries", code=_lambda.Code.from_asset(layer_dir),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13], compatible_architectures=[_lambda.Architecture.ARM_64],
            description="cdk12: openpyxl e paramiko (build_layer.sh)", removal_policy=RemovalPolicy.DESTROY)
        self.code = _lambda.Code.from_asset(os.path.join(ROOT, "lambda"), exclude=["__pycache__", "requirements.txt"])
        common_env = {**FOLDERS, "BUCKET_NAME": self.bucket.bucket_name}
        db_env = {"DB_CLUSTER_ARN": self.cluster.cluster_arn, "DB_SECRET_ARN": self.cluster.secret.secret_arn,
                  "DB_NAME": DB_NAME, "DB_TABLE": DB_TABLE}

        decompress = self.function("Decompress", "files.decompress", common_env, timeout=120, memory=1024)
        self.bucket.grant_read(decompress, "INPUT/*")
        self.bucket.grant_put(decompress, "DEZIPPED/*")

        convert = self.function("ConvertToCsv", "files.convert_to_csv", common_env, timeout=120, memory=1024, layer=True)
        self.bucket.grant_read(convert, "DEZIPPED/*")
        self.bucket.grant_put(convert, "CSV/*")

        process = self.function("ProcessCsv", "database.process_csv",
                                {**common_env, **db_env, "LOG_TABLE": self.log_table.table_name}, timeout=180,
                                retry_attempts=0)  # niente nuovi tentativi automatici: righe inserite due volte
        self.bucket.grant_read(process, "CSV/*")
        self.cluster.grant_data_api_access(process)
        self.log_table.grant(process, "dynamodb:PutItem")

        read_rds = self.function("ReadRdsData", "database.read_rds", db_env, timeout=28)
        self.cluster.grant_data_api_access(read_rds)

        api_env = {**common_env, "LOG_TABLE": self.log_table.table_name, "SCAN_TABLE": self.scan_table.table_name}
        api_functions = {
            "upload-zip": self.function("UploadZip", "api.upload_zip", api_env),
            "list-excel-files": self.function("ListExcelFiles", "api.list_excel_files", api_env),
            "download-excel-file": self.function("DownloadExcelFile", "api.download_excel_file", api_env),
            "read-rds-data": read_rds,
            "read-dynamodb-data": self.function("ReadDynamoDbData", "api.read_dynamodb_data", api_env),
            "list-new-files": self.function("ListNewFiles", "api.list_new_files", api_env),
            "find-file": self.function("FindFile", "api.find_file", api_env),
        }
        self.bucket.grant_put(api_functions["upload-zip"], "INPUT/*")  # l'URL prefirmato usa i permessi della Lambda
        self.bucket.grant_read(api_functions["list-excel-files"])
        self.bucket.grant_read(api_functions["download-excel-file"], "DEZIPPED/*")
        self.log_table.grant_read_data(api_functions["read-dynamodb-data"])
        self.scan_table.grant_read_data(api_functions["list-new-files"])
        self.scan_table.grant_read_data(api_functions["find-file"])

        scan = self.function("ScanS3", "scan.scan_bucket", api_env, timeout=300)
        self.bucket.grant_read(scan)
        self.scan_table.grant(scan, "dynamodb:PutItem", "dynamodb:UpdateItem")

        # ---- regole EventBridge ----
        def on_upload(name: str, patterns: list, function: _lambda.IFunction, description: str):
            events.Rule(self, f"{name}Rule", rule_name=nome_risorsa(self, name), description=description,
                event_pattern=events.EventPattern(source=["aws.s3"], detail_type=["Object Created"], detail={
                    "bucket": {"name": [self.bucket.bucket_name]},
                    "object": {"key": [{"wildcard": p} for p in patterns]}}),
                targets=[targets.LambdaFunction(function, retry_attempts=0)])

        on_upload("Decompress", ["INPUT/*.zip", "INPUT/*.tar", "INPUT/*.tar.gz", "INPUT/*.tgz"], decompress,
                  "cdk12: archivi caricati in INPUT/")
        on_upload("ConvertToCsv", ["DEZIPPED/*.xlsx"], convert, "cdk12: file Excel estratti in DEZIPPED/")
        on_upload("ProcessCsv", ["CSV/*.csv"], process, "cdk12: CSV in CSV/ da caricare nel database")
        events.Rule(self, "ScanSchedule", rule_name=nome_risorsa(self, "ScanS3"), description="cdk12: scansione del bucket alle 01:00 UTC",
                    schedule=events.Schedule.cron(minute="0", hour="1"), targets=[targets.LambdaFunction(scan)])

        sftp_host = self.node.try_get_context("sftp_host")
        if sftp_host:
            key_param = self.node.try_get_context("sftp_key_param") or "/cdk12/sftp/private-key"
            sftp = self.function("SendSftp", "sftp.send", {
                "SFTP_HOST": sftp_host, "SFTP_PORT": str(self.node.try_get_context("sftp_port") or 22),
                "SFTP_USER": self.node.try_get_context("sftp_user") or "sftp", "SFTP_KEY_PARAM": key_param},
                timeout=120, layer=True)
            self.bucket.grant_read(sftp, "TOSENDSFTP/*")
            sftp.add_to_role_policy(iam.PolicyStatement(actions=["ssm:GetParameter"], resources=[
                self.format_arn(service="ssm", resource="parameter", resource_name=key_param.lstrip("/"))]))
            on_upload("SendSftp", ["TOSENDSFTP/*"], sftp, "cdk12: file da inviare via SFTP")

        # ---- API REST ----
        self.api = apigw.RestApi(self, "Api", rest_api_name=nome_risorsa(self, "Api"), description="cdk12: API dei file S3",
            default_cors_preflight_options=apigw.CorsOptions(allow_origins=apigw.Cors.ALL_ORIGINS,
                                                             allow_methods=["GET", "OPTIONS"]),
            deploy_options=apigw.StageOptions(stage_name="dev", throttling_rate_limit=10, throttling_burst_limit=20,
                                              metrics_enabled=True))
        for route in API_ROUTES:
            self.api.root.add_resource(route).add_method("GET", apigw.LambdaIntegration(api_functions[route]))

        # ---- allarmi ----
        topic = sns.Topic(self, "AlarmTopic", topic_name=nome_risorsa(self, "Alarms"), display_name="Allarmi cdk12",
                          enforce_ssl=True)
        email = self.node.try_get_context("alarm_email")
        if email:
            topic.add_subscription(subscriptions.EmailSubscription(email))
        alarms = {
            "ProcessCsvErrors": process.metric_errors(period=Duration.minutes(5)),
            "ReadRdsDataErrors": read_rds.metric_errors(period=Duration.minutes(5)),
            "Api5xx": self.api.metric_server_error(period=Duration.minutes(5)),
        }
        for name, metric in alarms.items():
            alarm = cloudwatch.Alarm(self, f"{name}Alarm", alarm_name=nome_risorsa(self, name), metric=metric,
                threshold=1, evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING)
            alarm.add_alarm_action(cw_actions.SnsAction(topic))

        # ---- pagina web ----
        site = s3.Bucket(self, "SiteBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                         removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        distribution = cloudfront.Distribution(self, "Distribution", comment=f"{prefix} pagina web",
            default_root_object="index.html", price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS))
        s3deploy.BucketDeployment(self, "SiteDeployment", destination_bucket=site,
            sources=[s3deploy.Source.asset(os.path.join(ROOT, "web")),
                     s3deploy.Source.data("config.js", Fn.join("", ["window.API_ENDPOINT_CONFIG = '", self.api.url, "';\n"]))],
            distribution=distribution, distribution_paths=["/*"],
            log_group=logs.LogGroup(self, "SiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "LogTableName", value=self.log_table.table_name)
        CfnOutput(self, "ScanTableName", value=self.scan_table.table_name)
        CfnOutput(self, "DatabaseClusterArn", value=self.cluster.cluster_arn)
        CfnOutput(self, "DatabaseSecretArn", value=self.cluster.secret.secret_arn)
        CfnOutput(self, "AlarmTopicArn", value=topic.topic_arn)

    def function(self, name: str, handler: str, environment: dict, timeout: int = 15, memory: int = 256,
                 layer: bool = False, retry_attempts: int = 2) -> _lambda.Function:
        """Lambda Python 3.13 su ARM con log group dello stack (7 giorni, cancellato al destroy)."""
        function_name = nome_risorsa(self, name)
        log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{function_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        fn = _lambda.Function(self, name, function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
            handler=handler, code=self.code, environment=environment, layers=[self.layer] if layer else None,
            timeout=Duration.seconds(timeout), memory_size=memory, retry_attempts=retry_attempts, log_group=log_group)
        self.functions[name] = fn
        return fn
