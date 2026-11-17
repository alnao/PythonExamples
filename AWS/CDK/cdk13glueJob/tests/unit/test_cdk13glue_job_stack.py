import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk13glue_job.cdk13glue_job_stack import Cdk13GlueJobStack
from cdk13glue_job.naming import check_template
from cdk13glue_job.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::S3::BucketPolicy", "AWS::Lambda::LayerVersion"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk13"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk13GlueJobStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    tags = resource["Properties"].get("Tags", [])
    return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}  # Glue: tag come mappa


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_job():
    t = template()
    job = next(iter(t.find_resources("AWS::Glue::Job").values()))["Properties"]
    assert job["Name"] == "aws-py-cdk13-invert-csv" and job["GlueVersion"] == "5.0"
    assert job["WorkerType"] == "G.1X" and job["NumberOfWorkers"] == 2 and job["Timeout"] == 10
    assert job["Command"]["Name"] == "glueetl"
    args = job["DefaultArguments"]
    assert args["--continuous-log-logGroup"] == "/aws-glue/jobs/aws-py-cdk13-invert-csv"
    assert "INPUT/persone.csv" in json.dumps(args["--source_path"]) and "OUTPUT/" in json.dumps(args["--destination_path"])


def test_log_group_and_sample_data():
    t = template()
    t.has_resource("AWS::Logs::LogGroup", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like(
        {"LogGroupName": "/aws-glue/jobs/aws-py-cdk13-invert-csv", "RetentionInDays": 7})})
    t.has_resource_properties("Custom::CDKBucketDeployment", {"DestinationBucketKeyPrefix": "INPUT/", "Prune": False})


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
    """Ogni risorsa si chiama aws-py-cdk13-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
