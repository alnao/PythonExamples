import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk18efs.cdk18efs_stack import Cdk18EfsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk18efs/cdk18efs_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk18EfsStack(app, "cdk18efs")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
