import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk31elastic_beanstalk.cdk31elastic_beanstalk_stack import APP_DIR, HEALTH_PATH, Cdk31ElasticBeanstalkStack
from cdk31elastic_beanstalk.naming import check_template
from cdk31elastic_beanstalk.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::ElasticBeanstalk::Application", "AWS::ElasticBeanstalk::ApplicationVersion",
              "AWS::IAM::InstanceProfile"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk31"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk31ElasticBeanstalkStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_bundle_is_single_docker_container():
    dockerrun = json.loads((Path(APP_DIR) / "Dockerrun.aws.json").read_text())
    assert dockerrun["AWSEBDockerrunVersion"] == "1"
    assert dockerrun["Image"]["Name"] == "pathsgames/pathsgames"
    assert dockerrun["Ports"] == [{"ContainerPort": 8042}]
    assert sorted(p.name for p in Path(APP_DIR).iterdir()) == ["Dockerrun.aws.json"]


def test_application_and_version():
    t = template()
    t.has_resource_properties("AWS::ElasticBeanstalk::Application", {
        "ApplicationName": "aws-py-cdk31-app",
        "ResourceLifecycleConfig": assertions.Match.object_like({"VersionLifecycleConfig": {
            "MaxCountRule": {"Enabled": True, "MaxCount": 10, "DeleteSourceFromS3": False}}}),
    })
    version = next(iter(t.find_resources("AWS::ElasticBeanstalk::ApplicationVersion").values()))
    assert version["Properties"]["SourceBundle"]["S3Key"].endswith(".zip")
    assert version["Properties"]["ApplicationName"] == {"Ref": "Application"}  # dipendenza implicita


def test_environment_options():
    t = template()
    env = next(iter(t.find_resources("AWS::ElasticBeanstalk::Environment").values()))["Properties"]
    assert env["EnvironmentName"] == "aws-py-cdk31-env"
    assert env["SolutionStackName"] == {"Ref": "solutionstack"}
    options = {(o["Namespace"], o["OptionName"]): o["Value"] for o in env["OptionSettings"]}
    assert options[("aws:elasticbeanstalk:environment", "EnvironmentType")] == "LoadBalanced"
    assert options[("aws:elasticbeanstalk:environment", "LoadBalancerType")] == "application"
    assert options[("aws:elasticbeanstalk:environment:process:default", "HealthCheckPath")] == HEALTH_PATH
    assert options[("aws:elasticbeanstalk:environment:process:default", "Port")] == "80"
    assert options[("aws:autoscaling:launchconfiguration", "DisableIMDSv1")] == "true"
    assert options[("aws:ec2:instances", "InstanceTypes")] == {"Ref": "instancetype"}
    assert options[("aws:elasticbeanstalk:cloudwatch:logs", "DeleteOnTerminate")] == "true"


def test_roles():
    t = template()
    roles = t.find_resources("AWS::IAM::Role")
    principals = sorted(r["Properties"]["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]["Service"]
                        for r in roles.values())
    assert principals == ["ec2.amazonaws.com", "elasticbeanstalk.amazonaws.com"]
    t.resource_count_is("AWS::IAM::InstanceProfile", 1)


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e due sue subnet, per istanze e load balancer."""
    t = template()
    params = t.to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")
    env = next(iter(t.find_resources("AWS::ElasticBeanstalk::Environment").values()))["Properties"]
    vpc_options = {o["OptionName"]: o["Value"] for o in env["OptionSettings"] if o["Namespace"] == "aws:ec2:vpc"}
    subnets = {"Fn::Join": [",", [{"Ref": "subnetid1"}, {"Ref": "subnetid2"}]]}
    assert vpc_options == {"VPCId": {"Ref": "vpcid"}, "Subnets": subnets, "ELBSubnets": subnets,
                           "ELBScheme": "public", "AssociatePublicIpAddress": "true"}


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk31-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
