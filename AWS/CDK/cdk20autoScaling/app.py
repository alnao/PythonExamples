#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk20auto_scaling.cdk20auto_scaling_stack import Cdk20AutoScalingStack


app = cdk.App()

# tag standard su tutte le risorse dello stack (convenzione in CLAUDE.md)
TAGS = {
    "Name": "aws-py-CDK.cdk20autoScaling",
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk20autoScaling",
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

Cdk20AutoScalingStack(app, "Cdk20AutoScalingStack",
    synthesizer=SYNTHESIZER,
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
