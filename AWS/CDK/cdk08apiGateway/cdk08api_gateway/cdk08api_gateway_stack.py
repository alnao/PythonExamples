"""API Gateway REST con due stage (dev e prod) che invocano due alias della stessa Lambda.

- Lambda Python 3.13 (ARM) con due alias, dev e prod, sulla versione corrente del codice
- API REST con la risorsa GET /stage_info; l'integrazione chiama la funzione con l'alias scritto nella
  stage variable lambdaAlias: ogni stage invoca il "suo" alias
- un deployment e due stage (dev, prod) con limiti di richieste; ogni alias da' il permesso solo al suo stage
- niente log di esecuzione di API Gateway: richiederebbero il ruolo CloudWatch nelle impostazioni dell'account

Dall'esempio aws-samples api-stages-lambda:
https://github.com/aws-samples/aws-cdk-examples/tree/main/python/api-stages-lambda
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")
STAGES = ("dev", "prod")
PATH = "/stage_info"


class Cdk08ApiGatewayStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        function_name = nome_risorsa(self, "StageInfo")

        log_group = logs.LogGroup(self, "FunctionLogs", log_group_name=f"/aws/lambda/{function_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        function = _lambda.Function(self, "LambdaFunction", function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
            handler="function.handler", code=_lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"]),
            timeout=Duration.seconds(10), log_group=log_group)
        version = function.current_version
        aliases = {stage: _lambda.Alias(self, f"{stage.capitalize()}Alias", alias_name=stage, version=version)
                   for stage in STAGES}

        # API senza deployment automatico: deployment e stage sono dichiarati sotto
        self.api = apigw.RestApi(self, "Api", rest_api_name=nome_risorsa(self, "MultiStageApi"), deploy=False,
                                 description="cdk08: uno stage per ogni alias della Lambda")
        resource = self.api.root.add_resource(PATH.strip("/"))
        # l'URI dell'integrazione contiene la stage variable: API Gateway la sostituisce a ogni richiesta
        integration = apigw.AwsIntegration(service="lambda", proxy=True,
            path=f"2015-03-31/functions/{function.function_arn}:${{stageVariables.lambdaAlias}}/invocations")
        method = resource.add_method("GET", integration)

        deployment = apigw.Deployment(self, "Deployment", api=self.api, description="cdk08: dev e prod")
        deployment.node.add_dependency(method)

        self.stages = {}
        for stage_name, alias in aliases.items():
            stage = apigw.Stage(self, f"{stage_name.capitalize()}Stage", deployment=deployment, stage_name=stage_name,
                                variables={"lambdaAlias": alias.alias_name},
                                throttling_rate_limit=10, throttling_burst_limit=20, metrics_enabled=True)
            # il permesso vale solo per questo stage e questo alias
            alias.add_permission(f"{stage_name.capitalize()}StageInvoke",
                principal=iam.ServicePrincipal("apigateway.amazonaws.com"), action="lambda:InvokeFunction",
                source_arn=self.api.arn_for_execute_api(method="GET", path=PATH, stage=stage_name))
            self.stages[stage_name] = stage
            CfnOutput(self, f"{stage_name.capitalize()}Url", value=stage.url_for_path(PATH))
