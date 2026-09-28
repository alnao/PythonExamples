"""Step Functions: macchine a stati, definizione ed esecuzioni."""

from aws.services import paginate


class AwsStepFunctions:
    def __init__(self, session):
        self.client = session.client('stepfunctions')

    def state_machines(self):
        return paginate(self.client, 'list_state_machines', 'stateMachines')

    def detail(self, arn):
        detail = self.client.describe_state_machine(stateMachineArn=arn)
        detail.pop('ResponseMetadata', None)
        return detail

    def executions(self, arn, limit=100):
        return paginate(self.client, 'list_executions', 'executions', limit=limit, stateMachineArn=arn)
