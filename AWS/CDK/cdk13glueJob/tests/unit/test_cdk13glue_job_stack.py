import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk13glue_job.cdk13glue_job_stack import Cdk13GlueJobStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk13glue_job/cdk13glue_job_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Cdk13GlueJobStack(app, "cdk13glue-job")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
