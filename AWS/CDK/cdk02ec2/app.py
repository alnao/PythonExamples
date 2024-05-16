#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk02ec2.cdk02ec2_stack import Cdk02Ec2Stack


app = cdk.App()
Cdk02Ec2Stack(app, "Cdk02Ec2Stack",
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
