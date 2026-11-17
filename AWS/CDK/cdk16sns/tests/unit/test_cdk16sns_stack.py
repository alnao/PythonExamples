import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk16sns.cdk16sns_stack import Cdk16SnsStack
from cdk16sns.naming import check_template
from cdk16sns.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::SNS::Subscription", "AWS::SNS::TopicPolicy", "AWS::Lambda::Permission"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk16"


def template(**context):
    app = core.App(context={**CDK_CONTEXT, **context})
    apply_tags(app)
    stack = Cdk16SnsStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template(email="prova@example.com").to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_topic():
    t = template()
    t.has_resource_properties("AWS::SNS::Topic", {"TopicName": "aws-py-cdk16-notifications"})
    t.has_resource_properties("AWS::SNS::Subscription", {"Protocol": "lambda"})


def test_email_only_from_context():
    """Nessun indirizzo email nel codice: l'iscrizione email c'e' solo con -c email=..."""
    assert len(template().find_resources("AWS::SNS::Subscription")) == 1
    t = template(email="prova@example.com")
    t.has_resource_properties("AWS::SNS::Subscription", {"Protocol": "email", "Endpoint": "prova@example.com"})


def test_state_machine_publishes_to_topic():
    t = template()
    sm = next(iter(t.find_resources("AWS::StepFunctions::StateMachine").values()))["Properties"]
    assert sm["StateMachineName"] == "aws-py-cdk16-notify"
    assert ":states:::sns:publish" in json.dumps(sm["DefinitionString"])
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk16-logging", "Runtime": "python3.13"})


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
    """Ogni risorsa si chiama aws-py-cdk16-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
