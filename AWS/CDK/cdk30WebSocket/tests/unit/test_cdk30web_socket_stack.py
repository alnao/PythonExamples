import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk30web_socket.cdk30web_socket_stack import HTTP_ROUTES, Cdk30WebSocketStack
from cdk30web_socket.naming import check_template
from cdk30web_socket.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGatewayV2::Integration", "AWS::ApiGatewayV2::Route", "AWS::CloudFront::OriginAccessControl",
    "AWS::IAM::Policy", "AWS::Lambda::LayerVersion", "AWS::Lambda::Permission", "AWS::S3::BucketPolicy",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk30"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk30WebSocketStack(app, STACK_NAME)
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


def test_tables():
    t = template()
    names = {p["Properties"]["TableName"] for p in t.find_resources("AWS::DynamoDB::GlobalTable").values()}
    assert names == {"aws-py-cdk30-players", "aws-py-cdk30-matches", "aws-py-cdk30-logs", "aws-py-cdk30-bans"}
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {
        "TableName": "aws-py-cdk30-logs", "TimeToLiveSpecification": {"AttributeName": "expiresAt", "Enabled": True},
        "KeySchema": [{"AttributeName": "day", "KeyType": "HASH"}, {"AttributeName": "ts", "KeyType": "RANGE"}]})


def test_websocket_api():
    t = template()
    t.has_resource_properties("AWS::ApiGatewayV2::Api", {
        "ProtocolType": "WEBSOCKET", "RouteSelectionExpression": "$request.body.action"})
    ws_routes = {r["Properties"]["RouteKey"] for r in t.find_resources("AWS::ApiGatewayV2::Route").values()
                 if r["Properties"]["RouteKey"].startswith("$")}
    assert ws_routes == {"$connect", "$disconnect", "$default"}
    t.has_resource_properties("AWS::ApiGatewayV2::Stage", {"StageName": "prod", "AutoDeploy": True})


def test_http_api_routes_and_cors():
    t = template()
    t.has_resource_properties("AWS::ApiGatewayV2::Api", {"ProtocolType": "HTTP", "CorsConfiguration": assertions.Match.object_like({
        "AllowOrigins": ["*"], "AllowHeaders": ["content-type", "x-admin-key"]})})
    keys = {r["Properties"]["RouteKey"] for r in t.find_resources("AWS::ApiGatewayV2::Route").values()}
    assert {f"{m} {p}" for p, m in HTTP_ROUTES} <= keys
    t.has_resource_properties("AWS::ApiGatewayV2::Stage", {"StageName": "$default", "DefaultRouteSettings": {
        "ThrottlingRateLimit": 20, "ThrottlingBurstLimit": 40}})


def test_functions_can_post_to_connections():
    t = template()
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk30-api", "Handler": "api.handler",
        "Environment": {"Variables": assertions.Match.object_like({"WS_ENDPOINT": assertions.Match.any_value(),
                                                                  "ADMIN_SECRET_ARN": {"Ref": assertions.Match.string_like_regexp("AdminKey")}})}})
    for prefix in ("ApiServiceRole", "WebSocketServiceRole", "CleanupServiceRole"):
        statements = [s for lid, p in t.find_resources("AWS::IAM::Policy").items() if lid.startswith(prefix)
                      for s in p["Properties"]["PolicyDocument"]["Statement"]]
        assert any(s["Action"] == "execute-api:ManageConnections" for s in statements), prefix
    secret_readers = [lid for lid, p in t.find_resources("AWS::IAM::Policy").items()
                      if "secretsmanager:GetSecretValue" in json.dumps(p)]
    assert len(secret_readers) == 1 and secret_readers[0].startswith("ApiServiceRole")


def test_cleanup_schedule_and_secret():
    t = template()
    t.has_resource_properties("AWS::Events::Rule", {"ScheduleExpression": "rate(1 day)", "Name": "aws-py-cdk30-cleanup"})
    t.has_resource_properties("AWS::SecretsManager::Secret", {"Name": "aws-py-cdk30-admin-key",
        "GenerateSecretString": {"ExcludePunctuation": True, "PasswordLength": 32}})


def test_every_lambda_has_a_stack_log_group():
    """Anche le Lambda di supporto di CDK (es. svuotamento del bucket) scrivono in un log group dello stack, con i
    tag e cancellato al destroy, e non possono crearne altri: Lambda non crea log group senza tag e senza scadenza."""
    resources = template().to_json()["Resources"]
    functions = {k: v for k, v in resources.items() if v["Type"] == "AWS::Lambda::Function"}
    for logical_id, function in functions.items():
        log_group = function["Properties"]["LoggingConfig"]["LogGroup"]
        group_id = log_group["Ref"] if "Ref" in log_group else None
        if group_id:  # log group dello stack (le Lambda dell'esempio possono avere un nome fisso)
            assert resources[group_id]["Type"] == "AWS::Logs::LogGroup", logical_id
            assert resources[group_id]["DeletionPolicy"] == "Delete", logical_id
            assert resources[group_id]["Properties"]["RetentionInDays"] == 7, logical_id
    for logical_id, role in resources.items():
        if role["Type"] == "AWS::IAM::Role":
            assert "AWSLambdaBasicExecutionRole" not in json.dumps(role["Properties"].get("ManagedPolicyArns", [])), logical_id


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk30-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
    region) e ha il tag Name uguale al nome; le risorse senza nome (EC2, EFS, CloudFront, ...) hanno solo il tag Name."""
    assert check_template(template().to_json(), STACK_NAME) == []


def test_stack_tags(monkeypatch):
    """Lo stack CloudFormation ha i tag standard e Name uguale al suo nome: CDK li passa allo stack al deploy e
    CloudFormation li copia sulle risorse che non li hanno gia' (il Name scritto sulla risorsa vince)."""
    stacks, from_stack = [], assertions.Template.from_stack
    monkeypatch.setattr(assertions.Template, "from_stack",
                        staticmethod(lambda stack, *args, **kwargs: stacks.append(stack) or from_stack(stack, *args, **kwargs)))
    template()
    assert stacks[0].tags.tag_values() == {**TAGS, "Name": STACK_NAME}
