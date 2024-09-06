import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
)
from constructs import Construct

class Cdk09DynamoApiCrudStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Crea la tabella DynamoDB
        table = dynamodb.Table(
            self, "Cdk09Dynamo",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY  # Solo per ambiente di sviluppo
        )

        # Crea le funzioni Lambda
        create_lambda = self.create_lambda_function("CreateItemFunction", "create_item.lambda_handler", table)
        read_lambda = self.create_lambda_function("ReadItemFunction", "read_item.lambda_handler", table)
        update_lambda = self.create_lambda_function("UpdateItemFunction", "update_item.lambda_handler", table)
        delete_lambda = self.create_lambda_function("DeleteItemFunction", "delete_item.lambda_handler", table)

        # Crea l'API Gateway
        api = apigw.RestApi(self, "ItemsApi", rest_api_name="Items API")

        items = api.root.add_resource("items")
        items.add_method("POST", apigw.LambdaIntegration(create_lambda))
        items.add_method("GET", apigw.LambdaIntegration(read_lambda))
        
        item = items.add_resource("{id}")
        item.add_method("GET", apigw.LambdaIntegration(read_lambda))
        item.add_method("PUT", apigw.LambdaIntegration(update_lambda))
        item.add_method("DELETE", apigw.LambdaIntegration(delete_lambda))

    def create_lambda_function(self, id: str, handler: str, table: dynamodb.Table) -> lambda_.Function:
        lambda_fn = lambda_.Function(
            self, id,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler=handler,
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        
        table.grant_read_write_data(lambda_fn)
        return lambda_fn