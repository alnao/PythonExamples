#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk12lambda_application_s3_utils.cdk12lambda_application_s3_utils_stack import Cdk12LambdaApplicationS3UtilsStack
from cdk12lambda_application_s3_utils.tags import apply_tags


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

Cdk12LambdaApplicationS3UtilsStack(app, "aws-py-cdk12",
    synthesizer=SYNTHESIZER,
    # account e region del profilo AWS usato da cdk deploy: servono a CDK per leggere la VPC di default
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")),
    )

app.synth()
