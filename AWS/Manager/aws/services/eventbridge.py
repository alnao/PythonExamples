"""EventBridge: regole del bus di default, dettaglio con i target, attivazione e disattivazione."""

from aws.services import paginate


class AwsEventBridge:
    def __init__(self, session):
        self.client = session.client('events')

    def rules(self):
        return paginate(self.client, 'list_rules', 'Rules', EventBusName='default')

    def rule(self, name):
        detail = self.client.describe_rule(Name=name, EventBusName='default')
        detail.pop('ResponseMetadata', None)
        detail['Targets'] = paginate(self.client, 'list_targets_by_rule', 'Targets',
                                     Rule=name, EventBusName='default')
        return detail

    def set_enabled(self, name, enabled):
        if enabled:
            self.client.enable_rule(Name=name, EventBusName='default')
        else:
            self.client.disable_rule(Name=name, EventBusName='default')
        return self.rule(name)
