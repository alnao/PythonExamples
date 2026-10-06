"""CloudFormation: stack, parametri, output, risorse, eventi e template (sola lettura)."""

from aws.services import paginate


class AwsCloudFormation:
    def __init__(self, session):
        self.client = session.client('cloudformation')

    def stacks(self):
        """Stack attivi (describe_stacks non elenca quelli cancellati), con parametri, output e tag."""
        return paginate(self.client, 'describe_stacks', 'Stacks')

    def resources(self, stack):
        return paginate(self.client, 'list_stack_resources', 'StackResourceSummaries', StackName=stack)

    def events(self, stack, limit=100):
        """Eventi piu' recenti (AWS li restituisce gia' dal piu' nuovo)."""
        return paginate(self.client, 'describe_stack_events', 'StackEvents', limit=limit, StackName=stack)

    def template(self, stack):
        """Template originale: testo YAML o JSON (boto3 rende un dizionario se e' JSON)."""
        return self.client.get_template(StackName=stack, TemplateStage='Original').get('TemplateBody', '')
