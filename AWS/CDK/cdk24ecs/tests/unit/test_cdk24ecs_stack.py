import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk24ecs.cdk24ecs_stack import Cdk24EcsStack
from cdk24ecs.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::EC2::Route", "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SubnetRouteTableAssociation",
    "AWS::EC2::VPCGatewayAttachment", "AWS::ECS::ClusterCapacityProviderAssociations",
    "AWS::ElasticLoadBalancingV2::Listener", "AWS::ElasticLoadBalancingV2::ListenerRule",
    "AWS::IAM::InstanceProfile", "AWS::IAM::Policy",
}


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk24EcsStack(app, "cdk24")
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    if "Tags" in props:
        tags = props["Tags"]
        return tags if isinstance(tags, dict) else {t.get("Key", t.get("key")): t.get("Value", t.get("value")) for t in tags}
    for spec in props.get("TagSpecifications", []):
        return {t["Key"]: t["Value"] for t in spec["Tags"]}
    return {}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_vpc_with_one_nat():
    t = template()
    t.has_resource_properties("AWS::EC2::VPC", {"CidrBlock": "10.184.0.0/16"})
    t.resource_count_is("AWS::EC2::Subnet", 4)
    t.resource_count_is("AWS::EC2::NatGateway", 1)


def test_cluster_with_capacity_provider():
    t = template()
    t.has_resource_properties("AWS::ECS::Cluster", {"ClusterName": "cdk24"})
    t.has_resource_properties("AWS::ECS::CapacityProvider", {"AutoScalingGroupProvider": {
        "ManagedScaling": {"Status": "ENABLED", "TargetCapacity": 100},
        "ManagedTerminationProtection": "DISABLED", "ManagedDraining": "ENABLED",
    }})
    lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").values()))
    data = lt["Properties"]["LaunchTemplateData"]
    assert "ECS_CLUSTER" in str(data["UserData"])
    assert data["MetadataOptions"]["HttpTokens"] == "required"
    assert data["ImageId"]["Ref"].startswith("SsmParameterValueawsserviceecsoptimizedamiamazonlinux2023")


def test_task_and_service():
    t = template()
    t.has_resource_properties("AWS::ECS::TaskDefinition", {
        "NetworkMode": "bridge", "RequiresCompatibilities": ["EC2"],
        "ContainerDefinitions": [assertions.Match.object_like({
            "Name": "api-persone", "MemoryReservation": 256,
            "PortMappings": [{"ContainerPort": 5001, "HostPort": 0, "Protocol": "tcp"}],
        })],
    })
    t.has_resource_properties("AWS::ECS::Service", {
        "DesiredCount": 2, "PropagateTags": "SERVICE",
        "DeploymentConfiguration": assertions.Match.object_like(
            {"DeploymentCircuitBreaker": {"Enable": True, "Rollback": True}}),
    })
    t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": "/ecs/cdk24", "RetentionInDays": 7})


def test_load_balancer_routes():
    t = template()
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::ListenerRule", {
        "Priority": 10,
        "Conditions": [{"Field": "path-pattern", "PathPatternConfig": {"Values": ["/persone", "/persone/*", "/test"]}}],
    })
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::TargetGroup", {"HealthCheckPath": "/test"})
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::Listener", {
        "DefaultActions": [assertions.Match.object_like({"Type": "fixed-response"})]})


def test_image_from_existing_repository():
    """Con -c ecr_repository=... l'immagine e' quella del repository (es. cdk23ecr), non un asset."""
    t = template({"ecr_repository": "cdk23ecr-repository"})
    task = next(iter(t.find_resources("AWS::ECS::TaskDefinition").values()))
    image = task["Properties"]["ContainerDefinitions"][0]["Image"]
    assert "cdk23ecr-repository:latest" in str(image)


def test_launch_template_tags_instances_volumes_and_network_interfaces():
    """Istanze, volumi e interfacce di rete create dal launch template hanno i 6 tag standard."""
    for lt in template().find_resources("AWS::EC2::LaunchTemplate").values():
        specs = {s["ResourceType"]: {t["Key"]: t["Value"] for t in s["Tags"]}
                 for s in lt["Properties"]["LaunchTemplateData"]["TagSpecifications"]}
        assert specs == {"instance": TAGS, "volume": TAGS, "network-interface": TAGS}
        top = {t["Key"]: t["Value"] for t in lt["Properties"]["TagSpecifications"][0]["Tags"]}
        assert top == {**top, **TAGS}  # il launch template stesso
