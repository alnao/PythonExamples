import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk05lambda.cdk05lambda_stack import Cdk05LambdaStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk05lambda/cdk05lambda_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk05LambdaStack(app, "cdk05lambda")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
