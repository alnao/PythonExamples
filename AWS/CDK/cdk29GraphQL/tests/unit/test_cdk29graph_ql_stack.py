import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk29graph_ql.cdk29graph_ql_stack import Cdk29GraphQlStack
from cdk29graph_ql.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::AppSync::ApiKey", "AWS::AppSync::DataSource", "AWS::AppSync::GraphQLSchema", "AWS::AppSync::Resolver",
    "AWS::CloudFront::OriginAccessControl", "AWS::IAM::Policy", "AWS::Lambda::LayerVersion", "AWS::S3::BucketPolicy",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk29GraphQlStack(app, "cdk29")
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    if "Tags" in props:
        tags = props["Tags"]
        return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
    for replica in props.get("Replicas", []):
        return {t["Key"]: t["Value"] for t in replica.get("Tags", [])}
    return {}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_api_and_schema():
    t = template()
    t.has_resource_properties("AWS::AppSync::GraphQLApi", {
        "Name": "cdk29-listaNote", "AuthenticationType": "API_KEY",
        "LogConfig": assertions.Match.object_like({"FieldLogLevel": "ERROR", "ExcludeVerboseContent": True}),
    })
    schema = next(iter(t.find_resources("AWS::AppSync::GraphQLSchema").values()))["Properties"]["Definition"]
    for field in ("getNote: [Nota]", "addNota(testo: String!): Nota", "deleteNota(id: ID!): ID",
                  '@aws_subscribe(mutations: ["addNota"])', '@aws_subscribe(mutations: ["deleteNota"])'):
        assert field in schema
    t.resource_count_is("AWS::AppSync::ApiKey", 1)
    t.resource_count_is("Custom::LogRetention", 0)  # log group dello stack, non creato da una Lambda
    t.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7, "LogGroupName": {"Fn::Join": [
        "", ["/aws/appsync/apis/", {"Fn::GetAtt": [assertions.Match.string_like_regexp("Api"), "ApiId"]}]]}})


def test_resolvers_escape_input():
    """I valori degli argomenti passano da toDynamoDBJson: niente testo copiato a mano nel JSON (come nel CloudFormation)."""
    t = template()
    resolvers = {r["Properties"]["FieldName"]: r["Properties"] for r in t.find_resources("AWS::AppSync::Resolver").values()}
    assert set(resolvers) == {"getNote", "addNota", "deleteNota"}
    add = resolvers["addNota"]["RequestMappingTemplate"]
    assert "$util.dynamodb.toDynamoDBJson($ctx.args.testo)" in add and "$util.autoId()" in add and "$util.error" in add
    assert '"$ctx.args.testo"' not in add
    assert '"Scan"' in resolvers["getNote"]["RequestMappingTemplate"]
    assert "DeleteItem" in resolvers["deleteNota"]["RequestMappingTemplate"]


def test_table_and_data_source_permissions():
    t = template()
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {
        "TableName": "cdk29-listaNote", "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}]})
    t.has_resource_properties("AWS::AppSync::DataSource", {"Type": "AMAZON_DYNAMODB"})


def test_site():
    t = template()
    t.resource_count_is("AWS::CloudFront::Distribution", 1)
    deployment = next(iter(t.find_resources("Custom::CDKBucketDeployment").values()))["Properties"]
    assert "config.json" in json.dumps(deployment) or deployment["SourceMarkers"]
