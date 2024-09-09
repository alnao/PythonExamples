from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    CfnParameter,aws_logs as logs,
    CfnOutput,
)
from constructs import Construct

class Cdk10LambdaAuthStack(Stack):


    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Parametro per la chiave JWT
        jwt_secret = CfnParameter(self, "Cdk10JwtSecret", 
            type="String",
            description="Chiave segreta per la verifica del token JWT",
             default="alberto-na0-bello")

        stage_name = CfnParameter(self, "Cdk10StageName",
            type="String",
            description="Nome dello stage per l'API Gateway (es. dev, prod)",
            default="dev")

        # Lambda Authorizer
        authorizer_lambda = _lambda.Function(
            self, "Cdk10JwtAuthorizerLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="authorizer.handler",
            #code=_lambda.Code.from_asset("lambda"),
            code=_lambda.Code.from_asset("lambda",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_9.bundling_image,
                    "command": [
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                }
            ),
            environment={
                "JWT_SECRET": jwt_secret.value_as_string
            }
        )

        # Lambda Authorizer per API Gateway
        auth = apigw.TokenAuthorizer(
            self, "Cdk10JwtAuthorizer",
            handler=authorizer_lambda,
            results_cache_ttl=None  # Disabilita la cache per scopi di test
        )

        # API protetta
        api = apigw.RestApi(
            self, "ProtectedApi",
            deploy=False  # Importante: non deployare automaticamente
        )

        # Lambda per la risorsa protetta
        protected_lambda = _lambda.Function(
            self, "Cdk10ProtectedLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="protected.handler",
            code=_lambda.Code.from_asset("lambda")
        )

        # Integrazione della Lambda protetta con l'API
        protected_integration = apigw.LambdaIntegration(protected_lambda)

        # Aggiunta della risorsa protetta all'API con l'autorizzatore
        api.root.add_method("GET", protected_integration, authorizer=auth)

        # Creazione del deployment
        deployment = apigw.Deployment(self, "Cdk10Deployment", api=api)

        # Creazione dello stage
        stage = apigw.Stage(self, "Cdk10Stage",
            deployment=deployment,
            stage_name=stage_name.value_as_string,
            logging_level=apigw.MethodLoggingLevel.INFO,
            data_trace_enabled=True,
            throttling_rate_limit=10,
            throttling_burst_limit=5,
            metrics_enabled=True,
            access_log_destination=apigw.LogGroupLogDestination(logs.LogGroup(self, "Cdk10ApiGatewayAccessLogs")),
            access_log_format=apigw.AccessLogFormat.clf(),
        )

        # Aggiunta dello stage all'API
        api.deployment_stage = stage

        # Output dell'URL dell'API
        CfnOutput(self, "ApiUrl",
            value=f"{api.url}", #{stage_name.value_as_string}
            description="URL dell'API Gateway"
        )
