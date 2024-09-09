import json
import boto3
from datetime import datetime 
#see https://hands-on.cloud/boto3-sqs-tutorial/

#see https://github.com/boto/botocore/issues/2705
import warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='botocore.client')

class AwsSqs:
    def __init__(self, profile_name):
        self.profile_name=profile_name
    def get_sns_list(self):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        topics_iter = sqs_client.list_queues(
            #QueueNamePrefix='string',
            #NextToken='string',
            MaxResults=100
        )
        if 'QueueUrls' in topics_iter :
            return topics_iter['QueueUrls']
        return []

    def create_queue(self,queue_name,delay_seconds,visiblity_timeout):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        response = sqs_client.create_queue(QueueName=queue_name,
            Attributes={
                'DelaySeconds': str(delay_seconds),
                'VisibilityTimeout': str(visiblity_timeout)
                #  'FifoQueue': 'true'
            })
        return response

    def delete_queue(self, queue_name):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        response = sqs_client.delete_queue(QueueUrl=queue_name)
        return response

    def get_queue(self, queue_url):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        #response = sqs_client.get_queue_url(QueueName=queue_name)['QueueUrl']
        response = sqs_client.get_queue_attributes(    QueueUrl=queue_url, AttributeNames=['All'])
        if 'Attributes' in response:
            return response['Attributes']
        return {}
        
    def send_queue_message(self,queue_url,msg_attributes,msg_body):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        response = sqs_client.send_message(QueueUrl=queue_url,
            MessageAttributes=msg_attributes,
            MessageBody=msg_body)
        return response

    def receive_queue_messages(self,queue_url):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        response = sqs_client.receive_message(QueueUrl=queue_url,MaxNumberOfMessages=10)
        if 'Messages' in response:
            return response['Messages']
        return []

    def delete_queue_message(self,queue_url, receipt_handle):
        sqs_client = boto3.client("sqs") #, region_name=AWS_REGION
        response = sqs_client.delete_message(QueueUrl=queue_url,ReceiptHandle=receipt_handle)
        return response

def main(profile):
    print("Aws Py Console - SQS Instances START")
    o = AwsSqs("default")
    print ("----------------------------------------------------------------")
    
    #list
    lista= o.get_sns_list()
    print (lista)
    print ("----------------------------------------------------------------")
    QUEUE_URL=lista[1] 

    #get_queue
    res = o.get_queue( QUEUE_URL)
    json_msg = json.dumps(res, indent=4)
    print (json_msg)
    print ("----------------------------------------------------------------")
    
    #send_message
    MSG_ATTRIBUTES = {'Author': {'DataType': 'String','StringValue': 'Alberto Nao' }    }
    MSG_BODY = "{'messageEvent':'Message from SDK to SQS "+datetime.today().strftime('%Y%m%d %H%M%S')+"'}"
    res=o.send_queue_message(QUEUE_URL,MSG_ATTRIBUTES,MSG_BODY)
    #json_msg = json.dumps(res, indent=4)
    print( res )
    print ("----------------------------------------------------------------")

    #read messages
    messages = o.receive_queue_messages(QUEUE_URL)
    #print (messages)
    for msg in messages:
        #print (msg) MessageId,ReceiptHandle,Body, MD5OfBody
        msg_body = msg['Body']
        receipt_handle = msg['ReceiptHandle']
        print(f'The message body: {msg_body}')
        o.delete_queue_message(QUEUE_URL, receipt_handle)
    

    #delete topic
    #result= delete_queue("default","formazione-sqs-sdk" )
    #print(result)    

if __name__ == '__main__':
    main("default")