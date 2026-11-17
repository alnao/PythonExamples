"""Una funzione AWS Lambda in Python con il suo log group.

- runtime Python 3.13 su ARM (Graviton: costa circa il 20% in meno di x86)
- codice nella cartella lambda/, caricato da CDK come asset nel bucket del bootstrap
- log group creato dallo stack con scadenza a 7 giorni e cancellato al destroy: senza, Lambda lo crea
  da sola al primo avvio (senza tag e senza scadenza) e resta dopo il destroy
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk05LambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        function_name = nome_risorsa(self, "Hello")

        log_group = logs.LogGroup(self, "FunctionLogs", log_group_name=f"/aws/lambda/{function_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)

        self.function = _lambda.Function(self, "Function",
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_13,
            architecture=_lambda.Architecture.ARM_64,
            handler="cdk05lambda_code.lambda_handler",
            code=_lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"]),
            environment={"DEFAULT_NAME": "AlNao"},
            timeout=Duration.seconds(10),
            memory_size=128,
            log_group=log_group,
        )

        CfnOutput(self, "FunctionName", value=self.function.function_name)
        CfnOutput(self, "LogGroupName", value=log_group.log_group_name)
