#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk22cloud_watch_alarm.cdk22cloud_watch_alarm_stack import Cdk22CloudWatchAlarmStack
from cdk22cloud_watch_alarm.tags import apply_tags


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

Cdk22CloudWatchAlarmStack(app, "aws-py-cdk22",
    synthesizer=SYNTHESIZER,
    # account e region del profilo AWS usato da cdk deploy: servono a CDK per leggere la VPC di default
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")),
    )

app.synth()
