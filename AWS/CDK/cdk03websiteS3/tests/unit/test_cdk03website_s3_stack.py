import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk03website_s3.cdk03website_s3_stack import Cdk03WebsiteS3Stack
from cdk03website_s3.naming import check_template
from cdk03website_s3.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {"AWS::S3::BucketPolicy", "AWS::IAM::Policy", "AWS::Lambda::LayerVersion"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk03"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk03WebsiteS3Stack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_website_bucket():
    template().has_resource_properties("AWS::S3::Bucket", {
        "WebsiteConfiguration": {"IndexDocument": "index.html", "ErrorDocument": "error.html"},
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "IgnorePublicAcls": True,
                                           "BlockPublicPolicy": False, "RestrictPublicBuckets": False},
    })


def test_public_read_and_no_https_only_rule():
    """L'endpoint website e' solo HTTP: una Deny su aws:SecureTransport bloccherebbe il sito."""
    policy = next(iter(template().find_resources("AWS::S3::BucketPolicy").values()))
    statements = policy["Properties"]["PolicyDocument"]["Statement"]
    assert any(s["Effect"] == "Allow" and s["Action"] == "s3:GetObject" and s["Principal"] == {"AWS": "*"}
               for s in statements)
    assert not any("aws:SecureTransport" in json.dumps(s.get("Condition", {})) for s in statements)


def test_pages_deployed_with_log_group():
    t = template()
    t.resource_count_is("Custom::CDKBucketDeployment", 1)
    t.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7})
    t.has_resource("AWS::Logs::LogGroup", {"DeletionPolicy": "Delete"})


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
    """Ogni risorsa si chiama aws-py-cdk03-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
