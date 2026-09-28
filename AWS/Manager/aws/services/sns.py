"""SNS: topic, attributi, sottoscrizioni e pubblicazione di un messaggio."""

import json

from aws.services import paginate


class AwsSns:
    def __init__(self, session):
        self.client = session.client('sns')

    def topics(self):
        arns = [t['TopicArn'] for t in paginate(self.client, 'list_topics', 'Topics')]
        return [{'TopicArn': a, 'Name': a.rsplit(':', 1)[-1]} for a in arns]

    def attributes(self, topic_arn):
        return self.client.get_topic_attributes(TopicArn=topic_arn).get('Attributes', {})

    def subscriptions(self, topic_arn):
        return paginate(self.client, 'list_subscriptions_by_topic', 'Subscriptions', TopicArn=topic_arn)

    def publish(self, topic_arn, content):
        """Pubblica il testo nel formato del ManagerFlask: {"message": testo}."""
        return self.client.publish(TopicArn=topic_arn, Message=json.dumps({'message': content}))['MessageId']
