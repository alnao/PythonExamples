import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk27eks.cdk27eks_stack import Cdk27EksStack
from cdk27eks.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::EC2::SecurityGroupEgress", "AWS::EC2::SecurityGroupIngress"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk27EksStack(app, "cdk27")
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    if "Tags" in props:
        tags = props["Tags"]
        return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
    for spec in props.get("TagSpecifications", []):
        return {t["Key"]: t["Value"] for t in spec["Tags"]}
    return {}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_nodes_tagged_through_launch_template():
    lt = next(iter(template().find_resources("AWS::EC2::LaunchTemplate").values()))
    data = lt["Properties"]["LaunchTemplateData"]
    assert {s["ResourceType"] for s in data["TagSpecifications"]} >= {"instance", "volume"}
    assert data["MetadataOptions"] == {"HttpPutResponseHopLimit": 2, "HttpTokens": "required"}
    assert data["BlockDeviceMappings"][0]["Ebs"]["VolumeSize"] == 20


def test_parameters():
    params = template().to_json()["Parameters"]
    assert params["subnetids"]["Type"] == "List<AWS::EC2::Subnet::Id>"
    assert params["kubernetesversion"]["Default"] == "1.35"
    assert params["nodeinstancetype"]["Default"] == "t3.small"
    assert "adminprincipalarn" in params


def test_cluster():
    t = template()
    t.has_resource_properties("AWS::EKS::Cluster", {
        "Name": {"Ref": "clustername"}, "Version": {"Ref": "kubernetesversion"},
        "AccessConfig": {"AuthenticationMode": "API_AND_CONFIG_MAP", "BootstrapClusterCreatorAdminPermissions": True},
        "UpgradePolicy": {"SupportType": "STANDARD"},
        "Logging": {"ClusterLogging": {"EnabledTypes": [{"Type": "api"}, {"Type": "audit"}]}},
    })
    cluster = next(iter(t.find_resources("AWS::EKS::Cluster").values()))
    assert any(d.startswith("ClusterLogGroup") for d in cluster["DependsOn"])
    t.has_resource_properties("AWS::EKS::AccessEntry", {
        "PrincipalArn": {"Ref": "adminprincipalarn"},
        "AccessPolicies": [{"PolicyArn": "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
                            "AccessScope": {"Type": "cluster"}}],
    })


def test_nodegroup_and_addon():
    t = template()
    t.has_resource_properties("AWS::EKS::Nodegroup", {
        "AmiType": "AL2023_x86_64_STANDARD", "CapacityType": "ON_DEMAND",
        "ScalingConfig": {"MinSize": 1, "DesiredSize": 1, "MaxSize": 2},
        "InstanceTypes": [{"Ref": "nodeinstancetype"}],
    })
    addon = next(iter(t.find_resources("AWS::EKS::Addon").values()))
    assert addon["Properties"]["AddonName"] == "metrics-server"
    assert any(d.startswith("Nodegroup") for d in addon["DependsOn"])


def test_database_only_from_cluster():
    t = template()
    t.has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like({
        "Engine": "mysql", "EngineVersion": "8.4.8", "DBInstanceClass": "db.t4g.micro",
        "ManageMasterUserPassword": True, "StorageEncrypted": True, "PubliclyAccessible": False,
    })})
    sg = [s for s in t.find_resources("AWS::EC2::SecurityGroup").values()]
    assert len(sg) == 1
    rule = sg[0]["Properties"]["SecurityGroupIngress"]
    assert rule == [{"IpProtocol": "tcp", "FromPort": 3306, "ToPort": 3306, "Description": "MySQL dai nodi EKS",
                     "SourceSecurityGroupId": {"Fn::GetAtt": ["Cluster", "ClusterSecurityGroupId"]}}]


def test_launch_template_tags_instances_volumes_and_network_interfaces():
    """Istanze, volumi e interfacce di rete create dal launch template hanno i 6 tag standard."""
    for lt in template().find_resources("AWS::EC2::LaunchTemplate").values():
        specs = {s["ResourceType"]: {t["Key"]: t["Value"] for t in s["Tags"]}
                 for s in lt["Properties"]["LaunchTemplateData"]["TagSpecifications"]}
        assert specs == {"instance": TAGS, "volume": TAGS, "network-interface": TAGS}
        top = {t["Key"]: t["Value"] for t in lt["Properties"]["TagSpecifications"][0]["Tags"]}
        assert top == {**top, **TAGS}  # il launch template stesso
