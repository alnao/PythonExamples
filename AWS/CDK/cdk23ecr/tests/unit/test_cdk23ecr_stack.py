import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk23ecr.cdk23ecr_stack import Cdk23EcrStack
from cdk23ecr.naming import check_template
from cdk23ecr.tags import TAGS, apply_tags


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk23"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk23EcrStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_repository():
    t = template()
    t.resource_count_is("AWS::ECR::Repository", 1)
    t.has_resource("AWS::ECR::Repository", {
        "DeletionPolicy": "Delete",
        "Properties": {
            "RepositoryName": "aws-py-cdk23-repository",
            "ImageScanningConfiguration": {"ScanOnPush": True},
            "ImageTagMutability": "MUTABLE",
            "EmptyOnDelete": True,
        },
    })


def test_lifecycle_rules():
    repo = next(iter(template().find_resources("AWS::ECR::Repository").values()))
    rules = json.loads(repo["Properties"]["LifecyclePolicy"]["LifecyclePolicyText"])["rules"]
    assert [(r["rulePriority"], r["selection"]["tagStatus"], r["selection"]["countType"]) for r in rules] == [
        (1, "untagged", "sinceImagePushed"),
        (2, "any", "imageCountMoreThan"),
    ]
    assert rules[1]["selection"]["countNumber"] == 10


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk23-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
