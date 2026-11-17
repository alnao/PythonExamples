import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk04cloud_front.cdk04cloud_front_stack import Cdk04CloudFrontStack
from cdk04cloud_front.naming import check_template
from cdk04cloud_front.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {"AWS::S3::BucketPolicy", "AWS::IAM::Policy", "AWS::Lambda::LayerVersion",
              "AWS::CloudFront::OriginAccessControl"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk04"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk04CloudFrontStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_private_bucket():
    template().has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                           "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
    })


def test_distribution_with_origin_access_control():
    t = template()
    t.resource_count_is("AWS::CloudFront::OriginAccessControl", 1)
    t.resource_count_is("AWS::CloudFront::CloudFrontOriginAccessIdentity", 0)
    t.has_resource_properties("AWS::CloudFront::Distribution", {"DistributionConfig": assertions.Match.object_like({
        "DefaultRootObject": "index.html",
        "DefaultCacheBehavior": assertions.Match.object_like({"ViewerProtocolPolicy": "redirect-to-https"}),
    })})


def test_bucket_readable_only_by_cloudfront():
    policy = next(iter(template().find_resources("AWS::S3::BucketPolicy").values()))
    allows = [s for s in policy["Properties"]["PolicyDocument"]["Statement"] if s["Effect"] == "Allow"]
    reads = [s for s in allows if s["Action"] == "s3:GetObject"]
    assert reads and all(s["Principal"] == {"Service": "cloudfront.amazonaws.com"} for s in reads)
    assert all("AWS:SourceArn" in s["Condition"]["StringEquals"] for s in reads)


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
    """Ogni risorsa si chiama aws-py-cdk04-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
