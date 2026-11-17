"""AWS Step Functions che coordina due Lambda: avvio di un job e controllo periodico del suo stato.

Flusso: Submit Job -> Wait 10 secondi -> Get Status -> Choice
- status FAILED    -> Fail
- status SUCCEEDED -> Succeeded
- altrimenti       -> torna a Wait

Il job e' simulato dalle Lambda (lambda/submit.py e lambda/status.py): termina dopo "steps" controlli e
fallisce se l'input contiene "fail": true. Log della macchina a stati e delle Lambda in log group dello stack.
Ispirato all'esempio aws-samples:
https://github.com/aws-samples/aws-cdk-examples/blob/main/python/stepfunctions/stepfunctions/stepfunctions_stack.py
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

from .naming import nome_risorsa

LAMBDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lambda")


class Cdk07StepFunctionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        code = _lambda.Code.from_asset(LAMBDA_DIR, exclude=["__pycache__"])

        def function(name: str, handler: str) -> _lambda.Function:
            log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/aws/lambda/{nome_risorsa(self, name)}",
                                      retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            return _lambda.Function(self, name, function_name=nome_risorsa(self, name),
                runtime=_lambda.Runtime.PYTHON_3_13, architecture=_lambda.Architecture.ARM_64,
                handler=handler, code=code, timeout=Duration.seconds(10), log_group=log_group)

        submit_lambda = function("Submit", "submit.lambda_handler")
        status_lambda = function("Status", "status.lambda_handler")

        submit_job = tasks.LambdaInvoke(self, "Submit Job", lambda_function=submit_lambda, output_path="$.Payload")
        wait_job = sfn.Wait(self, "Wait 10 Seconds", time=sfn.WaitTime.duration(Duration.seconds(10)))
        status_job = tasks.LambdaInvoke(self, "Get Status", lambda_function=status_lambda, output_path="$.Payload")
        fail_job = sfn.Fail(self, "Fail", cause="Job fallito", error="JobFailed")
        succeed_job = sfn.Succeed(self, "Succeeded", comment="Job terminato")

        chain = (submit_job.next(wait_job).next(status_job)
                 .next(sfn.Choice(self, "Job Complete?")
                       .when(sfn.Condition.string_equals("$.status", "FAILED"), fail_job)
                       .when(sfn.Condition.string_equals("$.status", "SUCCEEDED"), succeed_job)
                       .otherwise(wait_job)))

        sm_logs = logs.LogGroup(self, "StateMachineLogs", log_group_name=f"/aws/vendedlogs/states/{nome_risorsa(self, 'Job')}",
                                retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        self.state_machine = sfn.StateMachine(self, "StateMachine",
            state_machine_name=nome_risorsa(self, "Job"),
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(10),
            logs=sfn.LogOptions(destination=sm_logs, level=sfn.LogLevel.ALL))

        CfnOutput(self, "StateMachineArn", value=self.state_machine.state_machine_arn)
