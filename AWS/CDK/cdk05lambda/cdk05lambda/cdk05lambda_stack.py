from aws_cdk import (
    aws_lambda as _lambda,
    aws_logs as logs,
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from constructs import Construct

class Cdk05LambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_function = _lambda.Function(self, "eventConsumer1Lambda",
                                                  runtime=_lambda.Runtime.PYTHON_3_12,
                                                  handler="cdk05lambda_code.lambda_handler",
                                                  code=_lambda.Code.from_asset("lambda")
                                                  )
        lambda_function.node.default_child.add_property_override(
            "FunctionName", f"cdk05lambda"
        )

        # Create new log group with the same name and add the dependencies.
        deployment_log_group = logs.LogGroup(
            self, "Cdk05lambda",
            log_group_name=f"/aws/lambda/cdk05lambda",
            #removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.TWO_WEEKS,
        )
        lambda_function.node.add_dependency(deployment_log_group)