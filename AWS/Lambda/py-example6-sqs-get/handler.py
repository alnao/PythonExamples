import json
import boto3
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    # TODO implement
    response = sqs.get_queue_url(
        QueueName='cherry-queue-formazione',
        QueueOwnerAWSAccountId='740456629644'
    )
    QueueUrl=response['QueueUrl']
    #print(response['QueueUrl'])
    response = sqs.receive_message(
        QueueUrl=QueueUrl,
        AttributeNames=['SentTimestamp'],
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    
    message = response['Messages'][0]
    receipt_handle = message['ReceiptHandle']
    body = message['Body']
    # Delete received message from queue
    sqs.delete_message(
        QueueUrl=QueueUrl,
        ReceiptHandle=receipt_handle
    )
    print('Received and deleted message: %s' % body)
    #print('Received and deleted message: %s' % message)
        
    return {
        'statusCode': 200,
        'body': body #json.dumps( body )
    }