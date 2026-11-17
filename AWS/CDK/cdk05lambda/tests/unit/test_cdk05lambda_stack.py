import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk05lambda.cdk05lambda_stack import Cdk05LambdaStack
from cdk05lambda.naming import check_template
from cdk05lambda.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::Policy"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk05"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk05LambdaStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_function():
    template().has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "aws-py-cdk05-hello",
        "Runtime": "python3.13",
        "Architectures": ["arm64"],
        "Handler": "cdk05lambda_code.lambda_handler",
        "LoggingConfig": {"LogGroup": {"Ref": assertions.Match.string_like_regexp("FunctionLogs")}},
    })


def test_log_group_deleted_with_the_stack():
    """Con Retain il log group restava dopo il destroy e il deploy successivo falliva (nome gia' usato)."""
    t = template()
    t.has_resource("AWS::Logs::LogGroup", {
        "DeletionPolicy": "Delete",
        "Properties": {"LogGroupName": "/aws/lambda/aws-py-cdk05-hello", "RetentionInDays": 7,
                       "Tags": assertions.Match.any_value()},
    })


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
    """Ogni risorsa si chiama aws-py-cdk05-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
