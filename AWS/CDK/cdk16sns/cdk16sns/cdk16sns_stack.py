"""Topic Amazon SNS con una Step Function che pubblica le notifiche e una Lambda che le riceve.

- topic <stack>-Notifications, solo HTTPS
- iscrizioni: una Lambda Python 3.13 (ARM) che scrive i messaggi nel log e, facoltativa, un indirizzo email
  passato con -c email=... (va confermato con il link che arriva)
- Step Function che pubblica sul topic il campo "message" dell'input (oggetto facoltativo in "subject")
- log group dello stack per la Lambda e per la Step Function, 7 giorni

La prima versione aveva un indirizzo email scritto nel codice e un topic con un nome generico (NotificationTopic).
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk16SnsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.topic = sns.Topic(self, "NotificationTopic", topic_name=nome_risorsa(self, "Notifications"),
                               display_name="Notifiche cdk16", enforce_ssl=True)

        function_name = nome_risorsa(self, "Logging")
        log_group = logs.LogGroup(self, "LoggingLogs", log_group_name=f"/aws/lambda/{function_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        logging_lambda = _lambda.Function(self, "LoggingLambda", function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
            handler="index.handler", code=_lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"]),
            timeout=Duration.seconds(10), log_group=log_group)
        self.topic.add_subscription(subscriptions.LambdaSubscription(logging_lambda))

        email = self.node.try_get_context("email")
        if email:
            self.topic.add_subscription(subscriptions.EmailSubscription(email))

        publish = tasks.SnsPublish(self, "SendToSNS", topic=self.topic,
            message=sfn.TaskInput.from_json_path_at("$.message"),
            subject=sfn.JsonPath.string_at("States.Format('cdk16: {}', $.subject)"),
            result_path="$.sns_result")
        default_subject = sfn.Pass(self, "DefaultSubject", parameters={"message.$": "$.message", "subject": "notifica"})
        has_subject = (sfn.Choice(self, "HasSubject")
                       .when(sfn.Condition.is_present("$.subject"), publish)
                       .otherwise(default_subject.next(publish)))

        sm_logs = logs.LogGroup(self, "StateMachineLogs", log_group_name=f"/aws/vendedlogs/states/{nome_risorsa(self, 'Notify')}",
                                retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        self.state_machine = sfn.StateMachine(self, "NotificationStateMachine",
            state_machine_name=nome_risorsa(self, "Notify"),
            definition_body=sfn.DefinitionBody.from_chainable(has_subject),
            timeout=Duration.minutes(5),
            logs=sfn.LogOptions(destination=sm_logs, level=sfn.LogLevel.ERROR))

        CfnOutput(self, "TopicArn", value=self.topic.topic_arn)
        CfnOutput(self, "StateMachineArn", value=self.state_machine.state_machine_arn)
        CfnOutput(self, "LoggingFunctionName", value=logging_lambda.function_name)
