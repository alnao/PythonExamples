import json
import os
import boto3

sqs = boto3.client('sqs')
queue_url = os.environ['QUEUE_URL']

def handler(event, context):
    print("consumer",event)
    try:
        # Ricevi messaggi dalla coda SQS
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10
        )

        # Processa i messaggi
        if 'Messages' in response:
            data=[]
            for message in response['Messages']:
                # Elabora il messaggio
                print(f"Messaggio ricevuto: {message['Body']}")
                
                # Elimina il messaggio dalla coda
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message['ReceiptHandle']
                )
                data.append( message['Body'] )
            
            return {
                'statusCode': 200,
                'body': json.dumps(data) # f"Elaborati {len(response['Messages'])} messaggi"
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps("Nessun messaggio da elaborare")
            }
    
    except Exception as e:
        print(f"Errore: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Errore durante l'elaborazione dei messaggi: {str(e)}")
        }