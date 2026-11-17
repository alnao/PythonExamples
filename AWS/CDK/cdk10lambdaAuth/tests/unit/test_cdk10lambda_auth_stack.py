import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk10lambda_auth.cdk10lambda_auth_stack import Cdk10LambdaAuthStack
from cdk10lambda_auth.naming import check_template
from cdk10lambda_auth.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::Lambda::Permission", "AWS::ApiGateway::Method",
              "AWS::ApiGateway::Deployment", "AWS::ApiGateway::Authorizer", "AWS::ApiGateway::Account"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk10"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk10LambdaAuthStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_no_secret_in_parameters():
    """Il segreto e' generato in Secrets Manager: nessun parametro con un valore di default in chiaro."""
    t = template()
    assert not [p for p in t.to_json().get("Parameters", {}) if p != "BootstrapVersion"]
    t.has_resource_properties("AWS::SecretsManager::Secret", {"Name": "aws-py-cdk10-jwt-secret",
        "GenerateSecretString": {"PasswordLength": 48, "ExcludePunctuation": True}})


def test_no_docker_bundling_and_no_stage_logging():
    """Il deploy non richiede Docker ne' il ruolo CloudWatch di API Gateway nelle impostazioni dell'account."""
    t = template()
    t.resource_count_is("AWS::ApiGateway::Account", 0)
    stage = next(iter(t.find_resources("AWS::ApiGateway::Stage").values()))["Properties"]
    assert stage["StageName"] == "dev" and "AccessLogSetting" not in stage
    assert all("LoggingLevel" not in s and not s.get("DataTraceEnabled") for s in stage.get("MethodSettings", []))


def test_authorizer():
    t = template()
    t.has_resource_properties("AWS::ApiGateway::Authorizer", {
        "Type": "TOKEN", "IdentitySource": "method.request.header.Authorization", "AuthorizerResultTtlInSeconds": 0})
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk10-authorizer", "Runtime": "python3.13",
        "Environment": {"Variables": {"JWT_SECRET_ARN": {"Ref": assertions.Match.string_like_regexp("JwtSecret")}}}})
    t.has_resource_properties("AWS::ApiGateway::Method", {"HttpMethod": "GET", "AuthorizationType": "CUSTOM"})


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
    """Ogni risorsa si chiama aws-py-cdk10-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
