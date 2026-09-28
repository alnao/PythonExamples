"""SQS: code, attributi, invio e ricezione (con cancellazione) dei messaggi."""

import json

from aws.services import paginate


class AwsSqs:
    def __init__(self, session):
        self.client = session.client('sqs')

    def queues(self):
        urls = paginate(self.client, 'list_queues', 'QueueUrls')
        return [{'QueueUrl': u, 'Name': u.rsplit('/', 1)[-1]} for u in urls]

    def attributes(self, queue_url):
        return self.client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['All']).get('Attributes', {})

    def send(self, queue_url, content):
        """Invia il testo nel formato del ManagerFlask: {"messageEvent": testo}."""
        return self.client.send_message(QueueUrl=queue_url,
                                        MessageBody=json.dumps({'messageEvent': content}))['MessageId']

    def consume(self, queue_url):
        """Riceve fino a 10 messaggi e li cancella dalla coda (come il ManagerFlask)."""
        messages = self.client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10,
                                               MessageAttributeNames=['All']).get('Messages', [])
        for m in messages:
            self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=m['ReceiptHandle'])
        return [{'MessageId': m['MessageId'], 'Body': m.get('Body', ''),
                 'Attributes': m.get('MessageAttributes', {})} for m in messages]
