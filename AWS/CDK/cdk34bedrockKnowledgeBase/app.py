#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk34bedrock_knowledge_base.cdk34bedrock_knowledge_base_stack import Cdk34BedrockKnowledgeBaseStack
from cdk34bedrock_knowledge_base.tags import apply_tags


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

Cdk34BedrockKnowledgeBaseStack(app, "Cdk34BedrockKnowledgeBaseStack",
    synthesizer=SYNTHESIZER,
    # region fissa: Francoforte
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="eu-central-1"),
    )

app.synth()
