#!/usr/bin/env python3
import os

import aws_cdk as cdk
import jsii

from cdk32wiki_s3_vector.cdk32wiki_s3_vector_stack import Cdk32WikiS3VectorStack


app = cdk.App()

# tag standard su tutte le risorse dello stack (convenzione in CLAUDE.md)
TAGS = {
    "Name": "aws-py-CDK.cdk32wikiS3Vector",
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk32wikiS3Vector",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "CDK",
}
for key, value in TAGS.items():
    cdk.Tags.of(app).add(key, value)


@jsii.implements(cdk.IAspect)
class TagRawResources:
    """Le risorse di supporto create da CDK come CfnResource (es. il provider che svuota i
    bucket al destroy) non ricevono i tag da Tags.of: li aggiunge direttamente."""

    def visit(self, node):
        if (isinstance(node, cdk.CfnResource) and not cdk.TagManager.is_taggable(node)
                and node.cfn_resource_type in ("AWS::IAM::Role", "AWS::Lambda::Function")):
            node.add_property_override("Tags", [{"Key": k, "Value": v} for k, v in TAGS.items()])


cdk.Aspects.of(app).add(TagRawResources())

# bootstrap CDK dell'account con i nomi del repository (vedi AWS/CDK/bootstrap/README.md)
SYNTHESIZER = cdk.DefaultStackSynthesizer(
    qualifier="alnaodev",
    file_assets_bucket_name="alnao-dev-cdk",
    image_assets_repository_name="alnao-dev-cdk",
    bootstrap_stack_version_ssm_parameter="/cdk-bootstrap/alnao/dev/version",
)

Cdk32WikiS3VectorStack(app, "Cdk32WikiS3VectorStack",
    synthesizer=SYNTHESIZER,
    # cartella con boto3 per le Lambda creata da build_layer.sh
    layer_dir=app.node.try_get_context("layer_dir") or "layer",
    # region fissa: Francoforte
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-central-1"),
    )

app.synth()
