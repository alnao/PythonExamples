import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk01_bucket_s3.cdk01_bucket_s3_stack import Cdk01BucketS3Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk01_bucket_s3/cdk01_bucket_s3_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk01BucketS3Stack(app, "cdk01-bucket-s3")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
