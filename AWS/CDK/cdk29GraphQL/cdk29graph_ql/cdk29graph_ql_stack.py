"""API GraphQL "listaNote" con AWS AppSync e DynamoDB, e una pagina web su CloudFront.

- schema in graphql/schema.graphql: query getNote, mutation addNota e deleteNota, subscription onAddNota e onDeleteNota
- resolver VTL direttamente su DynamoDB (nessuna Lambda); i valori passano da $util.dynamodb.toDynamoDBJson
- autenticazione con API key valida 365 giorni (CDK calcola la scadenza a ogni deploy)
- log degli errori dei resolver in CloudWatch (7 giorni)
- pagina web (web/) su S3 privato dietro CloudFront, con URL e chiave della API in config.json
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    Expiration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_appsync as appsync,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MAX_TESTO = 500

ADD_NOTA_REQUEST = """
#if($util.isNullOrBlank($ctx.args.testo) || $ctx.args.testo.length() > %d)
  $util.error("Il testo della nota e' obbligatorio (al massimo %d caratteri)", "ValidationError")
#end
{
  "version": "2018-05-29",
  "operation": "PutItem",
  "key": { "id": $util.dynamodb.toDynamoDBJson($util.autoId()) },
  "attributeValues": {
    "testo": $util.dynamodb.toDynamoDBJson($ctx.args.testo),
    "createdAt": $util.dynamodb.toDynamoDBJson($util.time.nowISO8601())
  }
}
""" % (MAX_TESTO, MAX_TESTO)

DELETE_NOTA_REQUEST = """
{
  "version": "2018-05-29",
  "operation": "DeleteItem",
  "key": { "id": $util.dynamodb.toDynamoDBJson($ctx.args.id) }
}
"""


class Cdk29GraphQlStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name

        api = appsync.GraphqlApi(self, "Api", name=f"{prefix}-listaNote",
            definition=appsync.Definition.from_file(os.path.join(ROOT, "graphql", "schema.graphql")),
            authorization_config=appsync.AuthorizationConfig(default_authorization=appsync.AuthorizationMode(
                authorization_type=appsync.AuthorizationType.API_KEY,
                api_key_config=appsync.ApiKeyConfig(name="web", description="chiave della pagina web",
                                                    expires=Expiration.after(Duration.days(365))))))
        # Log degli errori dei resolver: impostati sulla risorsa L1, perche' log_config dell'L2 aggiunge una Lambda
        # (LogRetention) che crea il log group senza tag; qui il log group e' dello stack, con tag e 7 giorni
        logs_role = iam.Role(self, "ApiLogsRole", assumed_by=iam.ServicePrincipal("appsync.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSAppSyncPushToCloudWatchLogs")])
        api.node.default_child.log_config = appsync.CfnGraphQLApi.LogConfigProperty(
            cloud_watch_logs_role_arn=logs_role.role_arn, field_log_level="ERROR", exclude_verbose_content=True)
        logs.LogGroup(self, "ApiLogs", log_group_name=Fn.join("", ["/aws/appsync/apis/", api.api_id]),
                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)

        table = dynamodb.TableV2(self, "NoteTable", table_name=f"{prefix}-listaNote",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(), removal_policy=RemovalPolicy.DESTROY)
        source = api.add_dynamo_db_data_source("NoteTableDataSource", table)

        source.create_resolver("GetNoteResolver", type_name="Query", field_name="getNote",
            request_mapping_template=appsync.MappingTemplate.dynamo_db_scan_table(),
            response_mapping_template=appsync.MappingTemplate.dynamo_db_result_list())
        source.create_resolver("AddNotaResolver", type_name="Mutation", field_name="addNota",
            request_mapping_template=appsync.MappingTemplate.from_string(ADD_NOTA_REQUEST),
            response_mapping_template=appsync.MappingTemplate.dynamo_db_result_item())
        source.create_resolver("DeleteNotaResolver", type_name="Mutation", field_name="deleteNota",
            request_mapping_template=appsync.MappingTemplate.from_string(DELETE_NOTA_REQUEST),
            response_mapping_template=appsync.MappingTemplate.from_string("$util.toJson($ctx.args.id)"))

        # Pagina web: bucket privato, CloudFront con Origin Access Control
        site = s3.Bucket(self, "SiteBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                         removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        distribution = cloudfront.Distribution(self, "Distribution", comment=f"{prefix} lista note",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS))
        s3deploy.BucketDeployment(self, "SiteDeployment", destination_bucket=site,
            sources=[s3deploy.Source.asset(os.path.join(ROOT, "web")),
                     s3deploy.Source.json_data("config.json", {"graphqlUrl": api.graphql_url, "apiKey": api.api_key})],
            distribution=distribution, distribution_paths=["/*"],
            log_group=logs.LogGroup(self, "SiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "GraphQLApiUrl", value=api.graphql_url)
        CfnOutput(self, "GraphQLApiKey", value=api.api_key or "")
        CfnOutput(self, "GraphQLApiId", value=api.api_id)
        CfnOutput(self, "DynamoTableName", value=table.table_name)
        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
