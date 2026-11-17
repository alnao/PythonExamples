import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk24ecs.cdk24ecs_stack import Cdk24EcsStack
from cdk24ecs.naming import check_template
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
STACK_NAME = "aws-py-cdk24"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk24EcsStack(app, STACK_NAME, env=ENV)
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


def test_default_vpc_without_nat():
    """Per default la VPC di default della region e due sue subnet: nessuna VPC nuova e nessun NAT gateway."""
    t = template()
    for kind in ("AWS::EC2::VPC", "AWS::EC2::Subnet", "AWS::EC2::NatGateway", "AWS::EC2::EIP"):
        t.resource_count_is(kind, 0)
    params = t.to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")
    t.has_resource_properties("AWS::AutoScaling::AutoScalingGroup", {
        "VPCZoneIdentifier": [{"Ref": "subnetid1"}, {"Ref": "subnetid2"}]})
    lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").values()))["Properties"]["LaunchTemplateData"]
    assert lt["NetworkInterfaces"][0]["AssociatePublicIpAddress"] is True


def test_cluster_with_capacity_provider():
    t = template()
    t.has_resource_properties("AWS::ECS::Cluster", {"ClusterName": "aws-py-cdk24-cluster"})
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
    t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": "/ecs/aws-py-cdk24-api-persone", "RetentionInDays": 7})


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
        assert set(specs) == {"instance", "volume", "network-interface"}
        for tags in specs.values():  # tag standard e Name delle risorse lanciate (aws-py-cdkXX-<servizio>)
            assert tags == {**TAGS, "Name": specs["instance"]["Name"]} and tags["Name"].startswith(STACK_NAME + "-")
        top = {t["Key"]: t["Value"] for t in lt["Properties"]["TagSpecifications"][0]["Tags"]}
        assert top == {**top, **TAGS}  # il launch template stesso


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk24-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
