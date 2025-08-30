import json
import boto3
from datetime import datetime
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    # TODO implement
    response = sqs.get_queue_url(
        QueueName='cherry-queue-formazione',
        QueueOwnerAWSAccountId='740456629644'
    )
    QueueUrl=response['QueueUrl']
    
    oggetto={'arrivato':'si','messaggio':'ciao mondo', 'createdAt': str (datetime.now() )}
    
    response = sqs.send_message(
		QueueUrl=QueueUrl,
		DelaySeconds=10,
		MessageBody=(
			json.dumps( oggetto )
		)
	)
    return {
        'statusCode': 200,
        'body': json.dumps( response )
    }