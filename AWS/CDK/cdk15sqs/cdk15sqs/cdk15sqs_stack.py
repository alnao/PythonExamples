"""Coda Amazon SQS con due Lambda esposte da API Gateway: una invia i messaggi, l'altra li legge.

- coda standard cifrata (SSE-SQS), solo HTTPS, visibility timeout 60 secondi
- dead-letter queue: un messaggio letto 3 volte senza essere cancellato finisce nella DLQ (conservato 14 giorni)
- Lambda Python 3.13 (ARM): producer con il solo permesso di inviare, consumer con quello di leggere e cancellare
- API Gateway REST: POST /produce e GET /consume, stage dev con limite di richieste
- log group dello stack per le Lambda, 7 giorni

Ispirato all'esempio aws-samples s3-sns-sqs-lambda-chain:
https://github.com/aws-samples/aws-cdk-examples/blob/main/python/s3-sns-sqs-lambda-chain/s3_sns_sqs_lambda_chain/s3_sns_sqs_lambda_chain_stack.py
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_sqs as sqs,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk15SqsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.dead_letter_queue = sqs.Queue(self, "DeadLetterQueue", queue_name=nome_risorsa(self, "DLQ"),
            encryption=sqs.QueueEncryption.SQS_MANAGED, enforce_ssl=True,
            retention_period=Duration.days(14), removal_policy=RemovalPolicy.DESTROY)
        self.queue = sqs.Queue(self, "Queue", queue_name=nome_risorsa(self, "Queue"),
            encryption=sqs.QueueEncryption.SQS_MANAGED, enforce_ssl=True,
            visibility_timeout=Duration.seconds(60),
            dead_letter_queue=sqs.DeadLetterQueue(queue=self.dead_letter_queue, max_receive_count=3),
            removal_policy=RemovalPolicy.DESTROY)

        code = _lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__", "requirements.txt"])

        def function(name: str, handler: str) -> _lambda.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{nome_risorsa(self, name)}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            return _lambda.Function(self, name, function_name=nome_risorsa(self, name),
                runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
                handler=handler, code=code, environment={"QUEUE_URL": self.queue.queue_url},
                timeout=Duration.seconds(15), log_group=log_group)

        producer = function("Producer", "producer.handler")
        consumer = function("Consumer", "consumer.handler")
        self.queue.grant_send_messages(producer)
        self.queue.grant_consume_messages(consumer)

        self.api = apigw.RestApi(self, "Api", rest_api_name=nome_risorsa(self, "Api"),
            description="cdk15: producer e consumer della coda SQS",
            deploy_options=apigw.StageOptions(stage_name="dev", throttling_rate_limit=10, throttling_burst_limit=20))
        self.api.root.add_resource("produce").add_method("POST", apigw.LambdaIntegration(producer))
        self.api.root.add_resource("consume").add_method("GET", apigw.LambdaIntegration(consumer))

        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "QueueUrl", value=self.queue.queue_url)
        CfnOutput(self, "DeadLetterQueueUrl", value=self.dead_letter_queue.queue_url)
