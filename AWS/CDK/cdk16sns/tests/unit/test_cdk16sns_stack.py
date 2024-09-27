import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk16sns.cdk16sns_stack import Cdk16SnsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk16sns/cdk16sns_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk16SnsStack(app, "cdk16sns")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
