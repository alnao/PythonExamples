import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk08api_gateway.cdk08api_gateway_stack import Cdk08ApiGatewayStack
from cdk08api_gateway.naming import check_template
from cdk08api_gateway.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::Lambda::Permission", "AWS::Lambda::Version", "AWS::Lambda::Alias",
              "AWS::ApiGateway::Resource", "AWS::ApiGateway::Method", "AWS::ApiGateway::Deployment"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk08"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk08ApiGatewayStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_two_aliases_and_two_stages():
    t = template()
    for stage in ("dev", "prod"):
        t.has_resource_properties("AWS::Lambda::Alias", {"Name": stage})
        t.has_resource_properties("AWS::ApiGateway::Stage", {"StageName": stage, "Variables": {"lambdaAlias": stage}})


def test_integration_uses_stage_variable():
    """L'integrazione chiama l'alias scritto nella stage variable (la prima versione chiamava sempre $LATEST)."""
    method = next(iter(template().find_resources("AWS::ApiGateway::Method").values()))["Properties"]
    assert method["HttpMethod"] == "GET" and method["Integration"]["Type"] == "AWS_PROXY"
    assert ":${stageVariables.lambdaAlias}/invocations" in json.dumps(method["Integration"]["Uri"])


def test_each_alias_allows_only_its_stage():
    permissions = template().find_resources("AWS::Lambda::Permission")
    assert len(permissions) == 2
    for permission in permissions.values():
        props = permission["Properties"]
        alias = props["FunctionName"]["Ref"]
        stage = "dev" if alias.startswith("DevAlias") else "prod"
        assert f"/{stage}/GET/stage_info" in json.dumps(props["SourceArn"])


def test_deployment_after_method():
    t = template()
    deployment = next(iter(t.find_resources("AWS::ApiGateway::Deployment").values()))
    method_id = next(iter(t.find_resources("AWS::ApiGateway::Method")))
    assert method_id in deployment["DependsOn"]


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
    """Ogni risorsa si chiama aws-py-cdk08-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
