import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk23ecr.cdk23ecr_stack import Cdk23EcrStack
from cdk23ecr.tags import TAGS, apply_tags


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk23EcrStack(app, "cdk23")
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
            "RepositoryName": {"Ref": "reponame"},
            "ImageScanningConfiguration": {"ScanOnPush": True},
            "ImageTagMutability": "MUTABLE",
            "EmptyOnDelete": True,
        },
    })
    assert template().to_json()["Parameters"]["reponame"]["Default"] == "cdk23ecr-repository"


def test_lifecycle_rules():
    repo = next(iter(template().find_resources("AWS::ECR::Repository").values()))
    rules = json.loads(repo["Properties"]["LifecyclePolicy"]["LifecyclePolicyText"])["rules"]
    assert [(r["rulePriority"], r["selection"]["tagStatus"], r["selection"]["countType"]) for r in rules] == [
        (1, "untagged", "sinceImagePushed"),
        (2, "any", "imageCountMoreThan"),
    ]
    assert rules[1]["selection"]["countNumber"] == 10
