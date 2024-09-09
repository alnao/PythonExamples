from aws_cdk import (
    Stack,CfnParameter,
    Duration, #https://github.com/aws-samples/aws-cdk-examples/blob/main/python/s3-sns-sqs-lambda-chain/s3_sns_sqs_lambda_chain/s3_sns_sqs_lambda_chain_stack.py
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct

class Cdk15SqsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.queue_name = CfnParameter(self, "QueueName", type="String", default="cdk-sqs-es15").value_as_string


        # Creazione della coda SQS standard
        queue = sqs.Queue(
            self, "Cdk15Queue",
            queue_name=self.queue_name,
            visibility_timeout=Duration.seconds(300) #=300
        )

        # Creazione della funzione Lambda consumer
        consumer_lambda = _lambda.Function(
            self, "Cdk15ConsumerLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="consumer.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUEUE_URL": queue.queue_url
            }
            ,timeout = Duration.seconds(300)
        )

        # Creazione della funzione Lambda producer
        producer_lambda = _lambda.Function(
            self, "Cdk15ProducerLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="producer.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUEUE_URL": queue.queue_url
            }
            ,timeout = Duration.seconds(300)
        )

        # Concedi le autorizzazioni necessarie
        queue.grant_consume_messages(consumer_lambda)
        queue.grant_send_messages(producer_lambda)

        # Crea API Gateway per esporre le funzioni Lambda
        api = apigw.RestApi(self, "Cdk15MyApi")

        consumer_integration = apigw.LambdaIntegration(consumer_lambda)
        producer_integration = apigw.LambdaIntegration(producer_lambda)

        api.root.add_resource("consume").add_method("GET", consumer_integration)
        api.root.add_resource("produce").add_method("POST", producer_integration)

#app = App()
#SqsLambdaStack(app, "SqsLambdaStack")
#app.synth()