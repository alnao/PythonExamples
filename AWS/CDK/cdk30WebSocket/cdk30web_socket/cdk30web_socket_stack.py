"""Gioco "indovina il numero" con API Gateway WebSocket per le notifiche in tempo reale.

- WebSocket API ($connect, $disconnect, $default) e HTTP API (gioco, classifica, storico, amministrazione)
- Lambda Python: api.py (HTTP), ws.py (WebSocket e pulizia), logica del gioco in game.py
- DynamoDB on-demand: Players, Matches, Logs (con scadenza dopo 30 giorni) e Bans
- chiave di amministrazione generata in Secrets Manager (header X-Admin-Key)
- regola EventBridge giornaliera che toglie i giocatori inattivi
- pagine web (web/) su S3 privato dietro CloudFront, con gli indirizzi delle API in config.json
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

HTTP_ROUTES = [
    ("/set-number", "POST"), ("/guess-number", "POST"),
    ("/scores", "GET"), ("/matches", "GET"), ("/logs", "GET"),
    ("/admin/ban", "POST"), ("/admin/unban", "POST"), ("/admin/bans", "GET"),
    ("/admin/broadcast", "POST"), ("/admin/reset", "POST"),
]


class Cdk30WebSocketStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name

        def table(name: str, pk: str, sk: str = None, ttl: str = None) -> dynamodb.TableV2:
            return dynamodb.TableV2(self, f"{name}Table", table_name=f"{prefix}-{name}",
                partition_key=dynamodb.Attribute(name=pk, type=dynamodb.AttributeType.STRING),
                sort_key=dynamodb.Attribute(name=sk, type=dynamodb.AttributeType.STRING) if sk else None,
                time_to_live_attribute=ttl, billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)
        tables = {
            "PLAYERS_TABLE": table("Players", "nickname"),
            "MATCHES_TABLE": table("Matches", "matchId"),
            "LOGS_TABLE": table("Logs", "day", "ts", ttl="expiresAt"),
            "BANS_TABLE": table("Bans", "nickname"),
        }

        admin_key = secretsmanager.Secret(self, "AdminKey", secret_name=f"{prefix}-AdminKey",
            description="chiave delle API di amministrazione del gioco (header X-Admin-Key)",
            generate_secret_string=secretsmanager.SecretStringGenerator(exclude_punctuation=True, password_length=32),
            removal_policy=RemovalPolicy.DESTROY)

        # WebSocket API: l'endpoint di gestione (callback) serve alle Lambda per scrivere ai client
        ws_api = apigw.WebSocketApi(self, "WebSocketApi", api_name=f"{prefix}-ws",
                                    description="notifiche in tempo reale del gioco indovina il numero")
        ws_stage = apigw.WebSocketStage(self, "WebSocketStage", web_socket_api=ws_api, stage_name="prod", auto_deploy=True,
                                        throttle=apigw.ThrottleSettings(rate_limit=50, burst_limit=100))

        code = lambda_.Code.from_asset(os.path.join(ROOT, "lambda"), exclude=["__pycache__"])
        env = {**{k: t.table_name for k, t in tables.items()},
               "WS_ENDPOINT": ws_stage.callback_url, "ADMIN_SECRET_ARN": admin_key.secret_arn}

        def function(name: str, handler: str, timeout: int = 10) -> lambda_.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{prefix}-{name}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            fn = lambda_.Function(self, name, function_name=f"{prefix}-{name}",
                runtime=lambda_.Runtime.PYTHON_3_13, architecture=lambda_.Architecture.ARM_64,
                handler=handler, code=code, environment=env, log_group=log_group,
                timeout=Duration.seconds(timeout), memory_size=256)
            for t in tables.values():
                t.grant_read_write_data(fn)
            ws_api.grant_manage_connections(fn)
            return fn

        api_fn = function("Api", "api.handler", timeout=20)
        ws_fn = function("WebSocket", "ws.handler")
        cleanup_fn = function("Cleanup", "ws.cleanup", timeout=60)
        admin_key.grant_read(api_fn)

        ws_integration = integrations.WebSocketLambdaIntegration("WebSocketIntegration", ws_fn)
        for route in ("$connect", "$disconnect", "$default"):
            ws_api.add_route(route, integration=ws_integration)

        # HTTP API con CORS: le pagine stanno su CloudFront, le API su execute-api
        http_api = apigw.HttpApi(self, "HttpApi", api_name=f"{prefix}-http", create_default_stage=False,
            cors_preflight=apigw.CorsPreflightOptions(allow_origins=["*"], max_age=Duration.hours(1),
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                allow_headers=["content-type", "x-admin-key"]))
        apigw.HttpStage(self, "HttpStage", http_api=http_api, stage_name="$default", auto_deploy=True,
                        throttle=apigw.ThrottleSettings(rate_limit=20, burst_limit=40))
        http_integration = integrations.HttpLambdaIntegration("ApiIntegration", api_fn)
        for path, method in HTTP_ROUTES:
            http_api.add_routes(path=path, methods=[apigw.HttpMethod(method)], integration=http_integration)

        # pulizia giornaliera dei giocatori inattivi
        events.Rule(self, "CleanupSchedule", rule_name=f"{prefix}-Cleanup", schedule=events.Schedule.rate(Duration.days(1)),
                    targets=[targets.LambdaFunction(cleanup_fn)])

        # Pagine web: bucket privato, CloudFront con Origin Access Control
        site = s3.Bucket(self, "SiteBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                         removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        distribution = cloudfront.Distribution(self, "Distribution", comment=f"{prefix} gioco indovina il numero",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS))
        s3deploy.BucketDeployment(self, "SiteDeployment", destination_bucket=site,
            sources=[s3deploy.Source.asset(os.path.join(ROOT, "web")),
                     s3deploy.Source.json_data("config.json", {"apiUrl": http_api.api_endpoint, "wsUrl": ws_stage.url})],
            distribution=distribution, distribution_paths=["/*"],
            log_group=logs.LogGroup(self, "SiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "HttpApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "WebSocketUrl", value=ws_stage.url)
        CfnOutput(self, "AdminKeyCommand", description="comando che legge la chiave di amministrazione",
                  value=f"aws secretsmanager get-secret-value --secret-id {admin_key.secret_name} --region {self.region}"
                        " --query SecretString --output text")
