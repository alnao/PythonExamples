"""Regole Amazon EventBridge che invocano una Lambda.

- bucket S3 dello stack con le notifiche verso EventBridge attive (event_bridge_enabled)
- regola sugli eventi "Object Created" del bucket per i file nella cartella INPUT/
- regola schedulata: dal lunedi' al venerdi' alle 18:00 UTC
- una Lambda Python 3.13 (ARM) riceve gli eventi delle due regole e li scrive nel log

La prima versione ascoltava un bucket esterno (prova-alberto) che lo stack non creava e su cui le notifiche
EventBridge andavano attivate a mano: ora il bucket e' nello stack.
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")
INPUT_PREFIX = "INPUT/"


class Cdk06EventBridgeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        function_name = nome_risorsa(self, "EventConsumer")

        self.bucket = s3.Bucket(self, "Bucket",
            event_bridge_enabled=True,  # S3 manda a EventBridge tutti gli eventi del bucket
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        log_group = logs.LogGroup(self, "FunctionLogs", log_group_name=f"/aws/lambda/{function_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        self.function = _lambda.Function(self, "EventConsumer",
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_13,
            architecture=_lambda.Architecture.ARM_64,
            handler="event_consumer_lambda.lambda_handler",
            code=_lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"]),
            timeout=Duration.seconds(10),
            log_group=log_group,
        )

        # File caricati nella cartella INPUT/ del bucket
        events.Rule(self, "ObjectCreatedRule", rule_name=nome_risorsa(self, "ObjectCreated"),
            description="cdk06: file caricati nella cartella INPUT/ del bucket",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"bucket": {"name": [self.bucket.bucket_name]},
                        "object": {"key": [{"prefix": INPUT_PREFIX}]}}),
            targets=[targets.LambdaFunction(self.function, retry_attempts=2)])

        # Dal lunedi' al venerdi' alle 18:00 UTC
        # see https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-scheduled-rule-pattern.html
        events.Rule(self, "ScheduleRule", rule_name=nome_risorsa(self, "Schedule"),
            description="cdk06: esecuzione schedulata dal lunedi' al venerdi' alle 18:00 UTC",
            schedule=events.Schedule.cron(minute="0", hour="18", month="*", week_day="MON-FRI", year="*"),
            targets=[targets.LambdaFunction(self.function)])

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "FunctionName", value=self.function.function_name)
        CfnOutput(self, "UploadCommand", value=f"aws s3 cp README.md s3://{self.bucket.bucket_name}/{INPUT_PREFIX}prova.md")
