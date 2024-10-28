import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk20auto_scaling.cdk20auto_scaling_stack import Cdk20AutoScalingStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk20auto_scaling/cdk20auto_scaling_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk20AutoScalingStack(app, "cdk20auto-scaling")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
