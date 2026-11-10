#!/usr/bin/env python3
import aws_cdk as cdk

from cdk26blockchain_lambda.cdk26blockchain_lambda_stack import Cdk26BlockchainLambdaStack
from cdk26blockchain_lambda.tags import apply_tags


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

Cdk26BlockchainLambdaStack(app, "Cdk26BlockchainLambdaStack",
    synthesizer=SYNTHESIZER,
    # stack senza env: account e region sono quelli del profilo AWS usato da cdk deploy
    )

app.synth()
