import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk15sqs.cdk15sqs_stack import Cdk15SqsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk15sqs/cdk15sqs_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk15SqsStack(app, "cdk15sqs")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
