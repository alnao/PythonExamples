import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk04cloud_front.cdk04cloud_front_stack import Cdk04CloudFrontStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk04cloud_front/cdk04cloud_front_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk04CloudFrontStack(app, "cdk04cloud-front")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
