import json
import re
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk17elastic_ip.cdk17elastic_ip_stack import Cdk17ElasticIpStack
from cdk17elastic_ip.naming import check_template
from cdk17elastic_ip.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::EC2::EIPAssociation", "AWS::IAM::InstanceProfile"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk17"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk17ElasticIpStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    """Ogni risorsa che accetta tag ha i 6 tag standard, comprese interfaccia di rete ed Elastic IP."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_elastic_ip_on_network_interface():
    t = template()
    t.has_resource_properties("AWS::EC2::EIP", {"Domain": "vpc"})
    t.has_resource_properties("AWS::EC2::EIPAssociation", {
        "AllocationId": {"Fn::GetAtt": ["ElasticIp", "AllocationId"]},
        "NetworkInterfaceId": {"Ref": "NetworkInterface"},
    })
    t.has_resource_properties("AWS::EC2::NetworkInterface", {"SubnetId": {"Ref": "subnetid"}})


def test_instance_uses_the_network_interface():
    t = template()
    props = next(iter(t.find_resources("AWS::EC2::Instance").values()))["Properties"]
    assert props["NetworkInterfaces"] == [{"DeviceIndex": "0", "NetworkInterfaceId": {"Ref": "NetworkInterface"}}]
    assert "SubnetId" not in props and "SecurityGroupIds" not in props
    assert props["PropagateTagsToVolumeOnCreation"] is True
    assert props["MetadataOptions"]["HttpTokens"] == "required"
    assert props["BlockDeviceMappings"][0]["Ebs"] == {"VolumeSize": 8, "VolumeType": "gp3", "Encrypted": True,
                                                     "DeleteOnTermination": True}


def test_only_http_open():
    sg = next(iter(template().find_resources("AWS::EC2::SecurityGroup").values()))
    assert [r["FromPort"] for r in sg["Properties"]["SecurityGroupIngress"]] == [80]


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e le sue subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid"]["Default"],) == ("s-12345",)


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk17-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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


# caratteri ammessi da EC2 nelle descrizioni di security group, regole e interfacce di rete:
# niente apostrofi o lettere accentate (il primo deploy falliva con "Invalid ... description")
EC2_DESCRIPTION = re.compile(r"^[a-zA-Z0-9. _\-:/()#,@\[\]+=&;{}!$*]{0,255}$")


def ec2_descriptions(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if "Description" in key and isinstance(value, str):
                yield value
            yield from ec2_descriptions(value)
    elif isinstance(node, list):
        for value in node:
            yield from ec2_descriptions(value)


def test_ec2_descriptions_valid():
    for resource in template().to_json()["Resources"].values():
        if resource["Type"].startswith("AWS::EC2::"):
            for description in ec2_descriptions(resource.get("Properties", {})):
                assert EC2_DESCRIPTION.match(description), f"{resource['Type']}: {description!r}"
