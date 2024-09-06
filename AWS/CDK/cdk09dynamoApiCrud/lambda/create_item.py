import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    item = json.loads(event['body'])
    table.put_item(Item=item)
    return {
        'statusCode': 201,
        'body': json.dumps('Item created successfully')
    }