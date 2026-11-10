import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk28code_pipeline_cicd.cdk28code_pipeline_cicd_stack import Cdk28CodePipelineCicdStack
from cdk28code_pipeline_cicd.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::CloudFront::OriginAccessControl", "AWS::EC2::Route", "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SubnetRouteTableAssociation", "AWS::EC2::VPCGatewayAttachment",
    "AWS::ElasticLoadBalancingV2::Listener", "AWS::IAM::Policy", "AWS::S3::BucketPolicy",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk28CodePipelineCicdStack(app, "cdk28")
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    if "Tags" in props:
        tags = props["Tags"]
        return tags if isinstance(tags, dict) else {t.get("Key", t.get("key")): t.get("Value", t.get("value")) for t in tags}
    return {}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_vpc_without_nat():
    t = template()
    t.resource_count_is("AWS::EC2::NatGateway", 0)
    t.resource_count_is("AWS::EC2::Subnet", 2)


def test_fargate_service():
    t = template()
    t.has_resource_properties("AWS::ECS::TaskDefinition", {
        "RequiresCompatibilities": ["FARGATE"], "Cpu": "256", "Memory": "512", "NetworkMode": "awsvpc",
        "ContainerDefinitions": [assertions.Match.object_like({
            "Name": "backend", "PortMappings": [{"ContainerPort": 5001, "Protocol": "tcp"}]})],
    })
    t.has_resource_properties("AWS::ECS::Service", {
        "LaunchType": "FARGATE", "DesiredCount": 1,
        "NetworkConfiguration": {"AwsvpcConfiguration": assertions.Match.object_like({"AssignPublicIp": "ENABLED"})},
    })
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::TargetGroup", {
        "TargetType": "ip", "Port": 5001, "HealthCheckPath": "/test"})


def test_pipeline_stages():
    t = template()
    pipeline = next(iter(t.find_resources("AWS::CodePipeline::Pipeline").values()))["Properties"]
    assert pipeline["PipelineType"] == "V2"
    stages = {s["Name"]: [a["ActionTypeId"]["Provider"] for a in s["Actions"]] for s in pipeline["Stages"]}
    assert stages == {"Source": ["GitHub"], "Build": ["CodeBuild", "CodeBuild"], "Deploy": ["ECS", "S3"]}
    source = pipeline["Stages"][0]["Actions"][0]["Configuration"]
    assert source["Owner"] == "alnao" and source["Repo"] == "PythonExamples" and source["Branch"] == "master"
    assert source["PollForSourceChanges"] is True
    assert "github/codepipeline/token" in source["OAuthToken"]
    deploy = {a["ActionTypeId"]["Provider"]: a["Configuration"] for a in pipeline["Stages"][2]["Actions"]}
    assert deploy["ECS"]["FileName"] == "imagedefinitions.json"
    assert deploy["S3"]["Extract"] == "true" and deploy["S3"]["CacheControl"] == "no-cache"


def test_codestar_connection_source():
    t = template({"connection_arn": "arn:aws:codeconnections:eu-central-1:123456789012:connection/abc"})
    pipeline = next(iter(t.find_resources("AWS::CodePipeline::Pipeline").values()))["Properties"]
    source = pipeline["Stages"][0]["Actions"][0]
    assert source["ActionTypeId"]["Provider"] == "CodeStarSourceConnection"
    assert source["Configuration"]["FullRepositoryId"] == "alnao/PythonExamples"


def test_build_projects():
    t = template()
    projects = {p["Properties"]["Name"]: p["Properties"] for p in t.find_resources("AWS::CodeBuild::Project").values()}
    assert set(projects) == {"cdk28-backend", "cdk28-frontend"}
    assert projects["cdk28-backend"]["Environment"]["PrivilegedMode"] is True
    spec = json.loads(projects["cdk28-backend"]["Source"]["BuildSpec"])
    assert "imagedefinitions.json" in spec["artifacts"]["files"]
    assert any("public.ecr.aws" in c for c in spec["phases"]["pre_build"]["commands"])
    env = {e["Name"]: e["Value"] for e in projects["cdk28-frontend"]["Environment"]["EnvironmentVariables"]}
    assert env["FRONTEND_DIR"] == "AWS/CDK/cdk28codePipelineCICD/frontend"
    for name in ("cdk28-backend", "cdk28-frontend"):
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/codebuild/{name}", "RetentionInDays": 7})


def test_cloudfront_routes_api_to_load_balancer():
    t = template()
    dist = next(iter(t.find_resources("AWS::CloudFront::Distribution").values()))["Properties"]["DistributionConfig"]
    patterns = sorted(b["PathPattern"] for b in dist["CacheBehaviors"])
    assert patterns == ["/persone*", "/test"]
    assert all(len(b["AllowedMethods"]) == 7 for b in dist["CacheBehaviors"])
    assert dist["DefaultRootObject"] == "index.html"
