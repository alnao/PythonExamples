import json
#import logging
#import os
#logger = logging.getLogger()
#logger.setLevel(logging.INFO)

def handler(event, context):
    print("Received event: " + json.dumps(event))
    
    for record in event['Records']:
        message = record['Sns']['Message']
        print(f"Received message: {message}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Message logged successfully')
    }