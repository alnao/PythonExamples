import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk19wordpress_single.cdk19wordpress_single_stack import Cdk19WordpressSingleStack
from cdk19wordpress_single.naming import check_template
from cdk19wordpress_single.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::EC2::EIPAssociation", "AWS::EC2::SecurityGroupIngress", "AWS::IAM::InstanceProfile",
              "AWS::IAM::Policy", "AWS::SecretsManager::SecretTargetAttachment"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk19"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk19WordpressSingleStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_database():
    t = template()
    t.has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like({
        "Engine": "mysql", "EngineVersion": "8.4.8", "DBInstanceClass": "db.t4g.micro", "DBName": {"Ref": "dbname"},
        "PubliclyAccessible": False, "StorageEncrypted": True, "DeleteAutomatedBackups": True})})
    ingress = next(iter(t.find_resources("AWS::EC2::SecurityGroupIngress").values()))["Properties"]
    assert "WebSecurityGroup" in json.dumps(ingress["SourceSecurityGroupId"])  # MySQL solo da WordPress


def test_instance_waits_for_signal_and_dependencies():
    t = template()
    instance = t.find_resources("AWS::EC2::Instance")["Instance"]
    assert instance["CreationPolicy"] == {"ResourceSignal": {"Count": 1, "Timeout": "PT15M"}}
    depends = instance["DependsOn"]
    assert "ElasticIpAssociation" in depends
    assert any(d.startswith("InstanceRoleDefaultPolicy") for d in depends)  # permesso di leggere il segreto
    assert any(d.startswith("DatabaseSecretAttachment") for d in depends)    # segreto con host e porta
    props = instance["Properties"]
    assert props["NetworkInterfaces"] == [{"DeviceIndex": "0", "NetworkInterfaceId": {"Ref": "NetworkInterface"}}]
    assert props["PropagateTagsToVolumeOnCreation"] is True
    script = json.dumps(props["UserData"])
    for piece in ("cfn-signal", "--resource Instance", "retry aws secretsmanager", "set +x", "ERRORE cdk19"):
        assert piece in script, piece


def test_elastic_ip_and_only_http():
    t = template()
    t.has_resource_properties("AWS::EC2::EIPAssociation", {"NetworkInterfaceId": {"Ref": "NetworkInterface"}})
    sg = t.find_resources("AWS::EC2::SecurityGroup")
    web = next(v for k, v in sg.items() if k.startswith("WebSecurityGroup"))
    assert [r["FromPort"] for r in web["Properties"]["SecurityGroupIngress"]] == [80]


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e le sue subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"],) == ("s-12345", "s-67890",)


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk19-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
