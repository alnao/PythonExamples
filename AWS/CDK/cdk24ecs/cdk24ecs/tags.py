"""Tag standard del repository (convenzione in CLAUDE.md) su tutte le risorse dell'app."""

import aws_cdk as cdk
import jsii
from aws_cdk import aws_ec2 as ec2

TAGS = {
    "Name": "aws-py-CDK.cdk24ecs",
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk24ecs",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "CDK",
}


@jsii.implements(cdk.IAspect)
class TagRawResources:
    """Le risorse di supporto create da CDK come CfnResource (es. il provider che svuota i
    bucket al destroy) non ricevono i tag da Tags.of: li aggiunge direttamente."""

    def visit(self, node):
        if (isinstance(node, cdk.CfnResource) and not cdk.TagManager.is_taggable(node)
                and node.cfn_resource_type in ("AWS::IAM::Role", "AWS::Lambda::Function")):
            node.add_property_override("Tags", [{"Key": k, "Value": v} for k, v in TAGS.items()])


# risorse create al lancio da un launch template: CDK tagga istanze e volumi, non le interfacce di rete
LAUNCH_TAG_TYPES = ("instance", "volume", "network-interface")


@jsii.implements(cdk.IAspect)
class TagLaunchTemplateResources:
    """Ogni launch template applica i tag standard a istanze, volumi e interfacce di rete che crea."""

    def visit(self, node):
        if isinstance(node, ec2.CfnLaunchTemplate):
            tags = [{"Key": k, "Value": v} for k, v in TAGS.items()]
            node.add_property_override("LaunchTemplateData.TagSpecifications",
                                       [{"ResourceType": t, "Tags": tags} for t in LAUNCH_TAG_TYPES])


def apply_tags(scope) -> None:
    """Tag su tutte le risorse sotto scope (l'app in app.py, la stessa chiamata nei test).
    Priorita' 300: vince sui tag Name che CDK mette da solo (es. sulle subnet della VPC)."""
    for key, value in TAGS.items():
        cdk.Tags.of(scope).add(key, value, priority=300)
    cdk.Aspects.of(scope).add(TagRawResources())
    cdk.Aspects.of(scope).add(TagLaunchTemplateResources())
