import json
import boto3
from datetime import datetime 
from botocore.exceptions import ClientError
#see https://hands-on.cloud/boto3-sqs-tutorial/

#see https://github.com/boto/botocore/issues/2705
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class AwsSns:
    def __init__(self, profile_name):
        self.profile_name=profile_name
        boto3.setup_default_session(profile_name=self.profile_name)
        self.sns_client = boto3.client('sns')#, region_name=region_name
        
    def create_topic(self, topic_name):
        try:
            response = self.sns_client.create_topic(Name=topic_name)
            return response['TopicArn']
        except ClientError as e:
            print(f"Error creating topic: {e}")
            return None

    def list_topics(self):
        try:
            response = self.sns_client.list_topics()
            return [topic['TopicArn'] for topic in response['Topics']]
        except ClientError as e:
            print(f"Error listing topics: {e}")
            return []

    def publish_message(self, topic_arn, message):
        try:
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Message=message
            )
            return response['MessageId']
        except ClientError as e:
            print(f"Error publishing message: {e}")
            return None

    def subscribe(self, topic_arn, protocol, endpoint):
        try:
            response = self.sns_client.subscribe(
                TopicArn=topic_arn,
                Protocol=protocol,
                Endpoint=endpoint
            )
            return response['SubscriptionArn']
        except ClientError as e:
            print(f"Error subscribing to topic: {e}")
            return None

    def list_subscriptions(self, topic_arn):
        try:
            response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            return response['Subscriptions']
        except ClientError as e:
            print(f"Error listing subscriptions: {e}")
            return []

    def unsubscribe(self, subscription_arn):
        try:
            self.sns_client.unsubscribe(SubscriptionArn=subscription_arn)
            return True
        except ClientError as e:
            print(f"Error unsubscribing: {e}")
            return False

    def set_topic_attributes(self, topic_arn, attribute_name, attribute_value):
        try:
            self.sns_client.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName=attribute_name,
                AttributeValue=attribute_value
            )
            return True
        except ClientError as e:
            print(f"Error setting topic attributes: {e}")
            return False

    def get_topic_attributes(self, topic_arn):
        try:
            response = self.sns_client.get_topic_attributes(TopicArn=topic_arn)
            return response['Attributes']
        except ClientError as e:
            print(f"Error getting topic attributes: {e}")
            return {}

    def delete_topic(self, topic_arn):
        try:
            self.sns_client.delete_topic(TopicArn=topic_arn)
            return True
        except ClientError as e:
            print(f"Error deleting topic: {e}")
            return False

# Example usage:
if __name__ == "__main__":
    sns = AwsSns("default")
    #topic_arn = sns.create_topic("MyTestTopic")
    l=sns.list_topics()
    for e in l:
        print(e)
    s=sns.list_subscriptions(l[-1])
    for sub in s:
        print(sub)
    messaggio={"messaggio":"prova messaggio da SDK per SNS"}
    sns.publish_message( l[-1] , json.dumps(messaggio) )


#    if topic_arn:
#        print(f"Topic created: {topic_arn}")
#        message_id = sns.publish_message(topic_arn, "Hello, SNS!")
#        if message_id:
#            print(f"Message published with ID: {message_id}")