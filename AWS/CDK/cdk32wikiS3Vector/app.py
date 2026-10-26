#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk32wiki_s3_vector.cdk32wiki_s3_vector_stack import Cdk32WikiS3VectorStack
from cdk32wiki_s3_vector.tags import apply_tags


app = cdk.App()

# tag standard su tutte le risorse dello stack (convenzione in CLAUDE.md)
apply_tags(app)

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
