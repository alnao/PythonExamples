import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk21auto_scaling_wordpress.cdk21auto_scaling_wordpress_stack import Cdk21AutoScalingWordpressStack
from cdk21auto_scaling_wordpress.naming import check_template
from cdk21auto_scaling_wordpress.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::EC2::SecurityGroupEgress", "AWS::EC2::SecurityGroupIngress", "AWS::EFS::MountTarget", "AWS::ElasticLoadBalancingV2::Listener",
    "AWS::IAM::InstanceProfile", "AWS::IAM::Policy", "AWS::SecretsManager::SecretTargetAttachment",
}


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk21"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk21AutoScalingWordpressStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    for key in ("Tags", "FileSystemTags"):
        if key in props:
            tags = props[key]
            return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
    for spec in props.get("TagSpecifications", []):
        return {t["Key"]: t["Value"] for t in spec["Tags"]}
    return {}


def test_all_resources_tagged():
    """Ogni risorsa che accetta tag ha i 6 tag standard; un tipo nuovo senza tag fa fallire il test."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_instances_tagged_at_launch():
    """Istanze e volumi creati dall'Auto Scaling group ricevono i tag (launch template e PropagateAtLaunch)."""
    t = template()
    lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").values()))
    specs = {s["ResourceType"]: s["Tags"] for s in lt["Properties"]["LaunchTemplateData"]["TagSpecifications"]}
    assert {"instance", "volume"} <= set(specs)
    asg = next(iter(t.find_resources("AWS::AutoScaling::AutoScalingGroup").values()))
    # tutti i tag passano alle istanze tranne Name: le istanze hanno il loro (dal launch template)
    assert all(tag["PropagateAtLaunch"] == (tag["Key"] != "Name") for tag in asg["Properties"]["Tags"])


def test_parameters():
    params = template().to_json()["Parameters"]
    for name in ("vpcid", "publicsubnetids1", "publicsubnetids2", "privatesubnetid1", "privatesubnetid2",
                 "instancetype", "dbname"):
        assert name in params
    assert params["instancetype"]["Default"] == "t3.micro"


def test_database_and_file_system():
    t = template()
    t.has_resource_properties("AWS::RDS::DBInstance", {
        "Engine": "mysql", "EngineVersion": "8.4.8", "StorageEncrypted": True, "DBInstanceClass": "db.t4g.micro",
        "MultiAZ": False, "PubliclyAccessible": False, "DeleteAutomatedBackups": True,
    })
    t.has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Delete"})
    t.has_resource_properties("AWS::EFS::FileSystem", {"Encrypted": True})
    t.resource_count_is("AWS::EFS::MountTarget", 2)


def test_auto_scaling_group_waits_for_signals():
    t = template()
    t.has_resource("AWS::AutoScaling::AutoScalingGroup", {
        "Properties": {"MinSize": "1", "MaxSize": "3", "HealthCheckType": "ELB"},
        "CreationPolicy": {"ResourceSignal": {"Timeout": "PT15M"}},
        "UpdatePolicy": {"AutoScalingRollingUpdate": assertions.Match.object_like(
            {"MinInstancesInService": 1, "MaxBatchSize": 1, "WaitOnResourceSignals": True})},
    })
    lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").values()))
    data = lt["Properties"]["LaunchTemplateData"]
    assert data["MetadataOptions"]["HttpTokens"] == "required"
    script = str(data["UserData"])
    assert "cfn-signal" in script and "flock 9" in script and "set +x" in script
    assert "retry mount -t efs" in script and "ERRORE cdk21" in script


def test_load_balancer_health_check_and_stickiness():
    t = template()
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::LoadBalancer", {"Scheme": "internet-facing"})
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::TargetGroup", {
        "HealthCheckPath": "/hostname.html", "Port": 80,
        "TargetGroupAttributes": assertions.Match.array_with([
            {"Key": "stickiness.enabled", "Value": "true"},
            {"Key": "stickiness.lb_cookie.duration_seconds", "Value": "30"},
        ]),
    })
    t.has_resource_properties("AWS::ElasticLoadBalancingV2::Listener", {"Port": 80, "Protocol": "HTTP"})


def test_no_ssh():
    """Accesso ai server con Session Manager: nessuna regola sulla porta 22."""
    for resource in template().to_json()["Resources"].values():
        for rule in resource.get("Properties", {}).get("SecurityGroupIngress", []):
            assert rule.get("FromPort") != 22
        if resource["Type"] == "AWS::EC2::SecurityGroupIngress":
            assert resource["Properties"].get("FromPort") != 22


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


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region: le stesse due subnet pubbliche per load balancer e istanze."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    for name, default in (("publicsubnetids1", "s-12345"), ("publicsubnetids2", "s-67890"),
                          ("privatesubnetid1", "s-12345"), ("privatesubnetid2", "s-67890")):
        assert params[name]["Default"] == default
    assert params["instancespublicip"]["Default"] == "true"


def test_instances_public_ip_from_parameter():
    """Senza NAT (VPC di default) le istanze hanno un IP pubblico; con subnet private si mette instancespublicip=false."""
    t = template()
    lt = next(iter(t.find_resources("AWS::EC2::LaunchTemplate").values()))["Properties"]["LaunchTemplateData"]
    assert lt["NetworkInterfaces"][0]["AssociatePublicIpAddress"] == {"Fn::If": ["InstancesPublicIp", True, False]}
    t.has_condition("InstancesPublicIp", {"Fn::Equals": [{"Ref": "instancespublicip"}, "true"]})


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk21-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
