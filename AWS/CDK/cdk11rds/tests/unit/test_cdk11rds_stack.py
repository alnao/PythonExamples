import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk11rds.cdk11rds_stack import Cdk11RdsStack
from cdk11rds.naming import check_template
from cdk11rds.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::SecretsManager::SecretTargetAttachment"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk11"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk11RdsStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


@pytest.mark.parametrize("context", [{}, {"aurora": "true"}])
def test_all_resources_tagged(context):
    for logical_id, resource in template(context).to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = {t["Key"]: t["Value"] for t in resource["Properties"].get("Tags", [])}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_mysql_instance_by_default():
    t = template()
    t.has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like({
        "Engine": "mysql", "EngineVersion": "8.4.8", "DBInstanceClass": "db.t4g.micro", "DBName": {"Ref": "dbname"},
        "StorageType": "gp3", "StorageEncrypted": True, "PubliclyAccessible": False, "MultiAZ": False,
        "DeleteAutomatedBackups": True,
    })})
    t.resource_count_is("AWS::RDS::DBCluster", 0)
    t.has_resource_properties("AWS::SecretsManager::Secret", {"GenerateSecretString": assertions.Match.object_like({
        "SecretStringTemplate": '{"username":"alnao"}', "GenerateStringKey": "password"})})


@pytest.mark.parametrize("engine,expected,port", [("mariadb", "mariadb", 3306), ("postgres", "postgres", 5432)])
def test_other_engines(engine, expected, port):
    t = template({"engine": engine})
    t.has_resource_properties("AWS::RDS::DBInstance", {"Engine": expected})
    sg = next(iter(t.find_resources("AWS::EC2::SecurityGroup").values()))
    assert sg["Properties"]["SecurityGroupIngress"] == [{"CidrIp": {"Ref": "allowedcidr"}, "Description": "accesso al database",
                                                          "FromPort": port, "IpProtocol": "tcp", "ToPort": port}]


def test_unknown_engine():
    with pytest.raises(Exception):
        template({"engine": "oracle"})


def test_aurora_serverless_with_pause_and_data_api():
    t = template({"aurora": "true"})
    t.has_resource("AWS::RDS::DBCluster", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like({
        "Engine": "aurora-mysql", "EnableHttpEndpoint": True, "StorageEncrypted": True,
        "ServerlessV2ScalingConfiguration": {"MinCapacity": 0, "MaxCapacity": 2, "SecondsUntilAutoPause": 300},
    })})
    t.has_resource_properties("AWS::RDS::DBInstance", {"DBInstanceClass": "db.serverless", "Engine": "aurora-mysql"})
    t.resource_count_is("AWS::SecretsManager::Secret", 2)


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region, due sue subnet e il suo CIDR (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")
    assert params["allowedcidr"]["Default"] == "1.2.3.4/5"


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk11-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
