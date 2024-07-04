import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk03website_s3.cdk03website_s3_stack import Cdk03WebsiteS3Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk03website_s3/cdk03website_s3_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk03WebsiteS3Stack(app, "cdk03website-s3")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
