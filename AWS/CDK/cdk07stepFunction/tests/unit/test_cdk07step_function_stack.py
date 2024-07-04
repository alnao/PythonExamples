import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk07step_function.cdk07step_function_stack import Cdk07StepFunctionStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk07step_function/cdk07step_function_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk07StepFunctionStack(app, "cdk07step-function")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
