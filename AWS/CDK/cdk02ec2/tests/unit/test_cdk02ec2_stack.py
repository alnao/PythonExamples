import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk02ec2.cdk02ec2_stack import Cdk02Ec2Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk02ec2/cdk02ec2_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk02Ec2Stack(app, "cdk02ec2")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
