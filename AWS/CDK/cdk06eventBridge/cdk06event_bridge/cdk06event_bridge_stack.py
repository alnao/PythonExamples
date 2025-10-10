from aws_cdk import (
    aws_lambda as _lambda,
#    aws_apigateway as api_gw,
    aws_events as events,
    aws_events_targets as targets,
#    aws_kinesisfirehose as _firehose,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    Stack
)
from constructs import Construct

class Cdk06EventBridgeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        event_consumer_lambda = _lambda.Function(self, "eventConsumer1Lambda",
                                                  runtime=_lambda.Runtime.PYTHON_3_8,
                                                  handler="event_consumer_lambda.lambda_handler",
                                                  code=_lambda.Code.from_asset("lambda")
                                                  )
        event_consumer_lambda.node.default_child.add_property_override(
            "FunctionName", f"cdk06event-bridge"
        )

        # Create new log group with the same name and add the dependencies.
        deployment_log_group = logs.LogGroup(
            self, "Cdk06eventBridge",
            log_group_name=f"/aws/lambda/cdk06event-bridge",
            #removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.TWO_WEEKS,
        )
        event_consumer_lambda.node.add_dependency(deployment_log_group)

        event_consumer_rule = events.Rule(self, 'cdk06eventbridge',
            description='cdk06 event bridge example',
            event_pattern=events.EventPattern(
                detail_type= ["Object Created"],
                source=["aws.s3"],
                detail={
                    "bucket": {
                        "name": ["prova-alberto"]
                    },
                    "object": {
                        "key": [{
                            "prefix": "INPUT"
                        }]
                    }
                }
            )
        )
        event_policy = iam.PolicyStatement(effect=iam.Effect.ALLOW, resources=['*'], actions=['events:PutEvents'])
        event_consumer_lambda.add_to_role_policy(event_policy)
        event_consumer_rule.add_target(targets.LambdaFunction(handler=event_consumer_lambda))

        # Run every day at 6PM UTC
        # See https://github.com/aws-samples/aws-cdk-examples/blob/main/python/lambda-cron/app.py
        # See https://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
        rule = events.Rule(
            self, "Rule",
            schedule=events.Schedule.cron(
                minute='0',
                hour='18',
                month='*',
                week_day='MON-FRI',
                year='*'),
        )
        rule.add_target(targets.LambdaFunction(handler=event_consumer_lambda))