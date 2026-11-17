import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk06event_bridge.cdk06event_bridge_stack import Cdk06EventBridgeStack
from cdk06event_bridge.naming import check_template
from cdk06event_bridge.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::S3::BucketPolicy", "AWS::Lambda::Permission"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk06"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk06EventBridgeStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_bucket_sends_events_to_eventbridge():
    template().has_resource_properties("Custom::S3BucketNotifications", {
        "NotificationConfiguration": {"EventBridgeConfiguration": {}},
    })


def test_object_created_rule_on_stack_bucket():
    t = template()
    bucket_id = next(iter(t.find_resources("AWS::S3::Bucket")))
    t.has_resource_properties("AWS::Events::Rule", {
        "Name": "aws-py-cdk06-object-created",
        "EventPattern": {
            "source": ["aws.s3"], "detail-type": ["Object Created"],
            "detail": {"bucket": {"name": [{"Ref": bucket_id}]}, "object": {"key": [{"prefix": "INPUT/"}]}},
        },
    })


def test_schedule_rule():
    template().has_resource_properties("AWS::Events::Rule", {
        "Name": "aws-py-cdk06-schedule", "ScheduleExpression": "cron(0 18 ? * MON-FRI *)",
    })


def test_function_and_log_group():
    t = template()
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk06-event-consumer", "Runtime": "python3.13"})
    t.has_resource("AWS::Logs::LogGroup", {"DeletionPolicy": "Delete",
                                           "Properties": assertions.Match.object_like(
                                               {"LogGroupName": "/aws/lambda/aws-py-cdk06-event-consumer"})})


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
    """Ogni risorsa si chiama aws-py-cdk06-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
