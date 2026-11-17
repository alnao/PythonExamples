import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk02ec2.cdk02ec2_stack import Cdk02Ec2Stack
from cdk02ec2.naming import check_template
from cdk02ec2.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::InstanceProfile"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk02"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk02Ec2Stack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def instance_props(t):
    return next(iter(t.find_resources("AWS::EC2::Instance").values()))["Properties"]


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        props = resource["Properties"]
        if resource["Type"] == "AWS::EC2::LaunchTemplate":
            props = props["TagSpecifications"][0]
        tags = {t["Key"]: t["Value"] for t in props.get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_disk_and_network_interface_tagged_by_launch_template():
    """EC2 crea disco e interfaccia di rete all'avvio: i tag arrivano dal launch template dell'istanza."""
    t = template()
    lt_id, lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").items()))
    specs = {s["ResourceType"]: {x["Key"]: x["Value"] for x in s["Tags"]}
             for s in lt["Properties"]["LaunchTemplateData"]["TagSpecifications"]}
    assert set(specs) == {"instance", "volume", "network-interface"}
    for tags in specs.values():
        assert tags == {**TAGS, "Name": "aws-py-cdk02-instance"}
    assert instance_props(t)["LaunchTemplate"]["LaunchTemplateId"] == {"Ref": lt_id}


def test_instance():
    props = instance_props(template())
    assert len(props["NetworkInterfaces"]) == 1
    eni = props["NetworkInterfaces"][0]
    assert eni["AssociatePublicIpAddress"] is True and eni["SubnetId"] == {"Ref": "subnetid"}
    assert "AvailabilityZone" not in props and "KeyName" not in props
    assert props["MetadataOptions"]["HttpTokens"] == "required"
    assert props["BlockDeviceMappings"][0]["Ebs"]["Encrypted"] is True


def test_no_inbound_ports():
    sg = next(iter(template().find_resources("AWS::EC2::SecurityGroup").values()))
    assert "SecurityGroupIngress" not in sg["Properties"]


def test_default_vpc_and_subnet():
    """Per default la VPC di default della region e una sua subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345" and params["vpcid"]["Type"] == "AWS::EC2::VPC::Id"
    assert params["subnetid"]["Default"] == "s-12345"


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk02-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
