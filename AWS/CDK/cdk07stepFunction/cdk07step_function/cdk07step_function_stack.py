from aws_cdk import (
    aws_stepfunctions as _aws_stepfunctions,
    aws_stepfunctions_tasks as _aws_stepfunctions_tasks,
    aws_lambda as _lambda,
    aws_logs as logs,
    App, Duration, Stack
)
from constructs import Construct

class Cdk07StepFunctionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        submit_lambda = _lambda.Function(self, 'submitLambda',
                                         handler='submit.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda'))

        status_lambda = _lambda.Function(self, 'statusLambda',
                                         handler='status.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda'))

        submit_lambda.node.default_child.add_property_override("FunctionName", f"cdk06submit")
        deployment_log_group = logs.LogGroup(
            self, "Cdk07stepFunctionSubmit",
            log_group_name=f"/aws/lambda/cdk06submit",
            retention=logs.RetentionDays.TWO_WEEKS,
        )
        submit_lambda.node.add_dependency(deployment_log_group)

        status_lambda.node.default_child.add_property_override("FunctionName", f"cdk06status")
        deployment_log_group2 = logs.LogGroup(
            self, "Cdk07stepFunctionStatus",
            log_group_name=f"/aws/lambda/cdk06status",
            retention=logs.RetentionDays.TWO_WEEKS,
        )
        status_lambda.node.add_dependency(deployment_log_group2)


        # Step functions Definition

        submit_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Submit Job",
            lambda_function=submit_lambda,
            output_path="$.Payload",
        )

        wait_job = _aws_stepfunctions.Wait(
            self, "Wait 30 Seconds",
            time=_aws_stepfunctions.WaitTime.duration(
                Duration.seconds(30))
        )

        status_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Get Status",
            lambda_function=status_lambda,
            output_path="$.Payload",
        )

        fail_job = _aws_stepfunctions.Fail(
            self, "Fail",
            cause='AWS Batch Job Failed',
            error='DescribeJob returned FAILED'
        )

        succeed_job = _aws_stepfunctions.Succeed(
            self, "Succeeded",
            comment='AWS Batch Job succeeded'
        )

        # Create Chain

        chain = submit_job.next(wait_job)\
            .next(status_job)\
            .next(_aws_stepfunctions.Choice(self, 'Job Complete?')
                  .when(_aws_stepfunctions.Condition.string_equals('$.status', 'FAILED'), fail_job)
                  .when(_aws_stepfunctions.Condition.string_equals('$.status', 'SUCCEEDED'), succeed_job)
                  .otherwise(wait_job))

        # Create state machine
        sm = _aws_stepfunctions.StateMachine(
            self, "StateMachine",
            definition_body=_aws_stepfunctions.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(50),
            state_machine_name= "Cdk07stepFunction",
        )
