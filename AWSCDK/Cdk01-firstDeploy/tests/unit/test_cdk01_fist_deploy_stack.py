import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk01_first_deploy.cdk01_first_deploy_stack import Cdk01FirstDeployStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk01_first_deploy/cdk01_first_deploy_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk01FirstDeployStack(app, "cdk01-first-deploy")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
