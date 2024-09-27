import aws_cdk as cdk
from aws_cdk import (
    Stack,Duration,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_lambda as _lambda,
    aws_iam as iam
)
from constructs import Construct

class Cdk16SnsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SNS Topic
        topic = sns.Topic(self, "Cdk16NotificationTopic",
            topic_name="NotificationTopic"
        )

        # Create Lambda function for logging
        logging_lambda = _lambda.Function(
            self, "Cdk16LoggingLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "TOPIC_ARN": topic.topic_arn
            }
            ,timeout = Duration.seconds(300)
        )
        logging_lambda.node.default_child.add_property_override(
            "FunctionName", f"cdk16Logging"
        )

        # Subscribe Lambda to SNS Topic
        topic.add_subscription(subscriptions.LambdaSubscription(logging_lambda))

        # Subscribe Email to SNS Topic
        topic.add_subscription(subscriptions.EmailSubscription("bellissimo@alnao.it"))

        # Create Step Function
        send_to_sns_task = sfn_tasks.SnsPublish(self, "Cdk16SendToSNS",
            topic=topic,
            message=sfn.TaskInput.from_json_path_at("$.message"),
            result_path="$.sns_result"
        )

        state_machine = sfn.StateMachine(self, "Cdk16NotificationStateMachine",
            state_machine_name="sfCdk16Sns"
            ,definition=send_to_sns_task
        )

        # Output the State Machine ARN
        cdk.CfnOutput(self, "Cdk16StateMachineArn",
            value=state_machine.state_machine_arn,
            description="State Machine ARN"
        )

