#!/usr/bin/env python3
import aws_cdk as cdk

from cdk21auto_scaling_wordpress.cdk21auto_scaling_wordpress_stack import Cdk21AutoScalingWordpressStack
from cdk21auto_scaling_wordpress.tags import apply_tags


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

Cdk21AutoScalingWordpressStack(app, "Cdk21AutoScalingWordpressStack",
    synthesizer=SYNTHESIZER,
    # stack senza env: account e region sono quelli del profilo AWS usato da cdk deploy
    )

app.synth()
