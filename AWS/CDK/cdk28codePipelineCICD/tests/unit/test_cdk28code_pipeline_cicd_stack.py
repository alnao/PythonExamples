import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk28code_pipeline_cicd.cdk28code_pipeline_cicd_stack import Cdk28CodePipelineCicdStack
from cdk28code_pipeline_cicd.naming import check_template
from cdk28code_pipeline_cicd.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::CloudFront::OriginAccessControl", "AWS::EC2::Route", "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SubnetRouteTableAssociation", "AWS::EC2::VPCGatewayAttachment",
    "AWS::ElasticLoadBalancingV2::Listener", "AWS::IAM::Policy", "AWS::S3::BucketPolicy",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk28"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk28CodePipelineCicdStack(app, STACK_NAME, env=ENV)
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


def test_default_vpc_without_nat():
    """Per default la VPC di default della region e due sue subnet: nessuna VPC nuova e nessun NAT gateway."""
    t = template()
    for kind in ("AWS::EC2::VPC", "AWS::EC2::Subnet", "AWS::EC2::NatGateway"):
        t.resource_count_is(kind, 0)
    params = t.to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")


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
    assert set(projects) == {"aws-py-cdk28-backend", "aws-py-cdk28-frontend"}
    assert projects["aws-py-cdk28-backend"]["Environment"]["PrivilegedMode"] is True
    spec = json.loads(projects["aws-py-cdk28-backend"]["Source"]["BuildSpec"])
    assert "imagedefinitions.json" in spec["artifacts"]["files"]
    assert any("public.ecr.aws" in c for c in spec["phases"]["pre_build"]["commands"])
    env = {e["Name"]: e["Value"] for e in projects["aws-py-cdk28-frontend"]["Environment"]["EnvironmentVariables"]}
    assert env["FRONTEND_DIR"] == "AWS/CDK/cdk28codePipelineCICD/frontend"
    for name in ("aws-py-cdk28-backend", "aws-py-cdk28-frontend"):
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/codebuild/{name}", "RetentionInDays": 7})


def test_cloudfront_routes_api_to_load_balancer():
    t = template()
    dist = next(iter(t.find_resources("AWS::CloudFront::Distribution").values()))["Properties"]["DistributionConfig"]
    patterns = sorted(b["PathPattern"] for b in dist["CacheBehaviors"])
    assert patterns == ["/persone*", "/test"]
    assert all(len(b["AllowedMethods"]) == 7 for b in dist["CacheBehaviors"])
    assert dist["DefaultRootObject"] == "index.html"


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
    """Ogni risorsa si chiama aws-py-cdk28-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
