"""API REST protetta da un Lambda authorizer che verifica un token JWT (HS256).

- segreto per firmare e verificare i token generato in Secrets Manager (nessuna password nei parametri)
- Lambda authorizer (tipo TOKEN, header Authorization) e Lambda della risorsa protetta, Python 3.13 su ARM
- la verifica JWT usa solo la libreria standard (lambda/jwt_hs256.py): niente pyjwt e niente Docker per il bundling
- API REST con GET / protetto, stage dev con limite di richieste e metriche
- niente log di esecuzione di API Gateway: richiedono il ruolo CloudWatch nelle impostazioni dell'account
  (AWS::ApiGateway::Account), un'impostazione unica per tutta la region che lo stack non deve toccare

La prima versione passava il segreto come parametro in chiaro con un default nel codice, faceva il bundling di
pyjwt con Docker e attivava i log dello stage: senza il ruolo CloudWatch dell'account il deploy falliva.
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
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk10LambdaAuthStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.jwt_secret = secretsmanager.Secret(self, "JwtSecret", secret_name=nome_risorsa(self, "JwtSecret"),
            description="cdk10: segreto HS256 per firmare e verificare i token JWT",
            generate_secret_string=secretsmanager.SecretStringGenerator(password_length=48, exclude_punctuation=True),
            removal_policy=RemovalPolicy.DESTROY)

        code = _lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__", "requirements.txt"])

        def function(name: str, handler: str, environment: dict = None) -> _lambda.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{nome_risorsa(self, name)}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            return _lambda.Function(self, name, function_name=nome_risorsa(self, name),
                runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
                handler=handler, code=code, environment=environment, timeout=Duration.seconds(10),
                log_group=log_group)

        authorizer_fn = function("Authorizer", "authorizer.handler", {"JWT_SECRET_ARN": self.jwt_secret.secret_arn})
        self.jwt_secret.grant_read(authorizer_fn)
        protected_fn = function("Protected", "protected.handler")

        authorizer = apigw.TokenAuthorizer(self, "JwtAuthorizer", handler=authorizer_fn,
            identity_source=apigw.IdentitySource.header("Authorization"),
            results_cache_ttl=Duration.seconds(0))  # nessuna cache: ogni richiesta verifica il token

        self.api = apigw.RestApi(self, "ProtectedApi", rest_api_name=nome_risorsa(self, "ProtectedApi"),
            description="cdk10: API protetta da un Lambda authorizer JWT",
            deploy_options=apigw.StageOptions(stage_name="dev", throttling_rate_limit=10, throttling_burst_limit=5,
                                              metrics_enabled=True))
        self.api.root.add_method("GET", apigw.LambdaIntegration(protected_fn), authorizer=authorizer)

        CfnOutput(self, "ApiUrl", value=self.api.url)
        CfnOutput(self, "JwtSecretArn", value=self.jwt_secret.secret_arn)
        CfnOutput(self, "TokenCommand", description="token di prova (dalla cartella del progetto)",
                  value=f"python3 make_token.py {self.jwt_secret.secret_arn} --region {self.region}")
