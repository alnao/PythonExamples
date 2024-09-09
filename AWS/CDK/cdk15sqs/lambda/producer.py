import json
import os
import boto3

sqs = boto3.client('sqs')
queue_url = os.environ['QUEUE_URL']

def handler(event, context):
    print("producer",event)
    try:
        # Estrai il messaggio dal corpo della richiesta
        body = json.loads(event['body']) if event.get('body') else {}
        message = body.get('message', 'Messaggio di default')

        # Invia il messaggio alla coda SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message
        )

        return {
            'statusCode': 200,
            'body': json.dumps(f"Messaggio inviato con successo. MessageId: {response['MessageId']}")
        }
    
    except Exception as e:
        print(f"Errore: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Errore durante l'invio del messaggio: {str(e)}")
        }