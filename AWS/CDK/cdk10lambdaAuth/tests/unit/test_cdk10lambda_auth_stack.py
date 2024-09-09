import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk10lambda_auth.cdk10lambda_auth_stack import Cdk10LambdaAuthStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk10lambda_auth/cdk10lambda_auth_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk10LambdaAuthStack(app, "cdk10lambda-auth")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
