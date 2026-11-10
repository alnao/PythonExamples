import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk31elastic_beanstalk.cdk31elastic_beanstalk_stack import APP_DIR, HEALTH_PATH, Cdk31ElasticBeanstalkStack
from cdk31elastic_beanstalk.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::ElasticBeanstalk::Application", "AWS::ElasticBeanstalk::ApplicationVersion",
              "AWS::IAM::InstanceProfile"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk31ElasticBeanstalkStack(app, "cdk31")
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
        "ApplicationName": "cdk31-app",
        "ResourceLifecycleConfig": assertions.Match.object_like({"VersionLifecycleConfig": {
            "MaxCountRule": {"Enabled": True, "MaxCount": 10, "DeleteSourceFromS3": False}}}),
    })
    version = next(iter(t.find_resources("AWS::ElasticBeanstalk::ApplicationVersion").values()))
    assert version["Properties"]["SourceBundle"]["S3Key"].endswith(".zip")
    assert version["Properties"]["ApplicationName"] == {"Ref": "Application"}  # dipendenza implicita


def test_environment_options():
    t = template()
    env = next(iter(t.find_resources("AWS::ElasticBeanstalk::Environment").values()))["Properties"]
    assert env["EnvironmentName"] == "cdk31-env"
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
