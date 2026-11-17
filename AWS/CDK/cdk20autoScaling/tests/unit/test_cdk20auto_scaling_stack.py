import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk20auto_scaling.cdk20auto_scaling_stack import Cdk20AutoScalingStack
from cdk20auto_scaling.naming import check_template
from cdk20auto_scaling.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::InstanceProfile", "AWS::IAM::Policy", "AWS::EC2::SecurityGroupIngress",
              "AWS::EC2::SecurityGroupEgress", "AWS::ElasticLoadBalancingV2::Listener",
              "AWS::AutoScaling::ScalingPolicy"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk20"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk20AutoScalingStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        props = resource["Properties"]
        if resource["Type"] == "AWS::EC2::LaunchTemplate":
            props = props["TagSpecifications"][0]
        tags = {t["Key"]: t["Value"] for t in props.get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_launch_template_tags_instances_disks_and_network_interfaces():
    lt = next(iter(template().find_resources("AWS::EC2::LaunchTemplate").values()))["Properties"]["LaunchTemplateData"]
    specs = {s["ResourceType"]: {t["Key"]: t["Value"] for t in s["Tags"]} for s in lt["TagSpecifications"]}
    assert set(specs) == {"instance", "volume", "network-interface"}
    assert all(tags == {**TAGS, "Name": "aws-py-cdk20-web-server"} for tags in specs.values())  # Name delle istanze
    assert lt["MetadataOptions"]["HttpTokens"] == "required"
    assert lt["NetworkInterfaces"][0]["AssociatePublicIpAddress"] is True
    assert "KeyName" not in lt


def test_asg_in_public_subnets_with_elb_health_check():
    t = template()
    t.has_resource_properties("AWS::AutoScaling::AutoScalingGroup", {
        "MinSize": "1", "MaxSize": "4", "DesiredCapacity": "2", "HealthCheckType": "ELB",
        "VPCZoneIdentifier": [{"Ref": "subnetid1"}, {"Ref": "subnetid2"}],
    })
    t.has_resource_properties("AWS::AutoScaling::ScalingPolicy", {"PolicyType": "TargetTrackingScaling"})


def test_instances_reachable_only_from_load_balancer():
    t = template()
    open_ports = [r for sg in t.find_resources("AWS::EC2::SecurityGroup").values()
                  for r in sg["Properties"].get("SecurityGroupIngress", [])]
    assert [(r["CidrIp"], r["FromPort"]) for r in open_ports] == [("0.0.0.0/0", 80)]  # solo il load balancer
    rules = t.find_resources("AWS::EC2::SecurityGroupIngress")
    assert [r["Properties"]["FromPort"] for r in rules.values()] == [80]
    assert all("SourceSecurityGroupId" in r["Properties"] for r in rules.values())


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e le sue subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"],) == ("s-12345", "s-67890",)


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk20-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
