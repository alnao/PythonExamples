#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk02ec2.cdk02ec2_stack import Cdk02Ec2Stack


app = cdk.App()

# tag standard su tutte le risorse dello stack (convenzione in CLAUDE.md)
TAGS = {
    "Name": "aws-py-CDK.cdk02ec2",
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk02ec2",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "CDK",
}
for key, value in TAGS.items():
    cdk.Tags.of(app).add(key, value)

# bootstrap CDK dell'account con i nomi del repository (vedi AWS/CDK/bootstrap/README.md)
SYNTHESIZER = cdk.DefaultStackSynthesizer(
    qualifier="alnaodev",
    file_assets_bucket_name="alnao-dev-cdk",
    image_assets_repository_name="alnao-dev-cdk",
    bootstrap_stack_version_ssm_parameter="/cdk-bootstrap/alnao/dev/version",
)

Cdk02Ec2Stack(app, "Cdk02Ec2Stack",
    synthesizer=SYNTHESIZER,
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
