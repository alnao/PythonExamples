import json
import re
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk18efs.cdk18efs_stack import Cdk18EfsStack
from cdk18efs.naming import check_template
from cdk18efs.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::InstanceProfile", "AWS::IAM::Policy", "AWS::EFS::MountTarget",
              "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SecurityGroupEgress"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk18"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk18EfsStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource["Properties"]
    if resource["Type"] == "AWS::EC2::LaunchTemplate":
        props = props["TagSpecifications"][0]
    return {t["Key"]: t["Value"] for t in props.get("Tags", props.get("FileSystemTags", []))}


def test_all_resources_tagged():
    """Tutti i tag standard, compreso Name (la prima versione aveva Name=Cdk18EfsStack/... su EFS e istanza)."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_disk_and_network_interface_tagged_by_launch_template():
    t = template()
    lt_id, lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").items()))
    specs = {s["ResourceType"] for s in lt["Properties"]["LaunchTemplateData"]["TagSpecifications"]}
    assert specs == {"instance", "volume", "network-interface"}
    instance = next(iter(t.find_resources("AWS::EC2::Instance").values()))
    assert instance["Properties"]["LaunchTemplate"]["LaunchTemplateId"] == {"Ref": lt_id}


def test_file_system_and_mount_target():
    t = template()
    t.has_resource("AWS::EFS::FileSystem", {"DeletionPolicy": "Delete",
                                            "Properties": assertions.Match.object_like({"Encrypted": True})})
    t.has_resource_properties("AWS::EFS::MountTarget", {"SubnetId": {"Ref": "subnetid"}})
    t.resource_count_is("AWS::EFS::MountTarget", 1)


def test_instance_and_user_data():
    t = template()
    instance = next(iter(t.find_resources("AWS::EC2::Instance").values()))
    props = instance["Properties"]
    assert "AvailabilityZone" not in props and "KeyName" not in props
    assert props["MetadataOptions"]["HttpTokens"] == "required"
    script = json.dumps(props["UserData"])
    assert "retry mount -t efs -o tls" in script and "X-aws-ec2-metadata-token" in script
    assert any(d.startswith("FileSystem") for d in instance["DependsOn"])


def test_only_http_and_nfs_from_instance():
    t = template()
    ingress = [r for sg in t.find_resources("AWS::EC2::SecurityGroup").values()
               for r in sg["Properties"].get("SecurityGroupIngress", [])]
    assert [r["FromPort"] for r in ingress] == [80]
    t.has_resource_properties("AWS::EC2::SecurityGroupIngress", {"FromPort": 2049, "ToPort": 2049})


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e le sue subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid"]["Default"],) == ("s-12345",)


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk18-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
