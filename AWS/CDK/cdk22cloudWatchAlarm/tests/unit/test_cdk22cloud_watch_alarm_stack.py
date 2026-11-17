import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk22cloud_watch_alarm.cdk22cloud_watch_alarm_stack import Cdk22CloudWatchAlarmStack
from cdk22cloud_watch_alarm.naming import check_template
from cdk22cloud_watch_alarm.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::AutoScaling::ScalingPolicy", "AWS::CloudWatch::Dashboard", "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::SecurityGroupIngress", "AWS::EFS::MountTarget", "AWS::ElasticLoadBalancingV2::Listener",
    "AWS::IAM::InstanceProfile", "AWS::IAM::Policy", "AWS::SNS::Subscription",
    "AWS::SecretsManager::SecretTargetAttachment",
}


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk22"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk22CloudWatchAlarmStack(app, STACK_NAME, env=ENV)
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
    """Ogni risorsa che accetta tag ha i 6 tag standard (quelli del cdk22, anche sulle risorse del cdk21)."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_contains_cdk21_infrastructure():
    t = template()
    for kind in ("AWS::AutoScaling::AutoScalingGroup", "AWS::ElasticLoadBalancingV2::LoadBalancer",
                 "AWS::RDS::DBInstance", "AWS::EFS::FileSystem"):
        t.resource_count_is(kind, 1)


def test_cpu_alarms_and_step_scaling():
    t = template()
    t.has_resource_properties("AWS::CloudWatch::Alarm", {
        "AlarmName": "aws-py-cdk22-cpu-high", "MetricName": "CPUUtilization", "Namespace": "AWS/EC2",
        "Statistic": "Average", "Period": 300, "EvaluationPeriods": 2, "Threshold": 84,
        "ComparisonOperator": "GreaterThanThreshold",
    })
    t.has_resource_properties("AWS::CloudWatch::Alarm", {
        "AlarmName": "aws-py-cdk22-cpu-low", "Threshold": 42, "ComparisonOperator": "LessThanThreshold",
    })
    policies = t.find_resources("AWS::AutoScaling::ScalingPolicy")
    steps = sorted(s["ScalingAdjustment"] for p in policies.values() for s in p["Properties"]["StepAdjustments"])
    assert steps == [-1, 1]
    for p in policies.values():
        assert p["Properties"]["PolicyType"] == "StepScaling"
        assert p["Properties"]["AdjustmentType"] == "ChangeInCapacity"


def test_health_alarms_notify_topic():
    t = template()
    for name in ("aws-py-cdk22-unhealthy-hosts", "aws-py-cdk22-load-balancer5xx"):
        t.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": name, "TreatMissingData": "notBreaching",
            "AlarmActions": [{"Ref": assertions.Match.string_like_regexp("AlarmTopic")}],
        })
    t.resource_count_is("AWS::CloudWatch::Alarm", 4)
    t.resource_count_is("AWS::CloudWatch::Dashboard", 1)


def test_email_subscription_only_with_context():
    template().resource_count_is("AWS::SNS::Subscription", 0)
    t = template({"alarm_email": "test@example.com"})
    t.has_resource_properties("AWS::SNS::Subscription", {"Protocol": "email", "Endpoint": "test@example.com"})


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


def test_default_vpc_from_cdk21():
    """Come il cdk21: per default la VPC di default della region (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345" and params["instancespublicip"]["Default"] == "true"


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk22-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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
