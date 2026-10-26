"""Tag standard del repository (convenzione in CLAUDE.md) su tutte le risorse dell'app."""

import aws_cdk as cdk
import jsii

TAGS = {
    "Name": "aws-py-CDK.cdk34bedrockKnowledgeBase",
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk34bedrockKnowledgeBase",
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


def apply_tags(scope) -> None:
    """Tag su tutte le risorse sotto scope (l'app in app.py, la stessa chiamata nei test)."""
    for key, value in TAGS.items():
        cdk.Tags.of(scope).add(key, value)
    cdk.Aspects.of(scope).add(TagRawResources())
