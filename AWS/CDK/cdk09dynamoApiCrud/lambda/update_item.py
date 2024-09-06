import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    item_id = event['pathParameters']['id']
    updates = json.loads(event['body'])
    update_expression = "SET " + ", ".join(f"#{k}=:{k}" for k in updates.keys())
    expression_attribute_names = {f"#{k}": k for k in updates.keys()}
    expression_attribute_values = {f":{k}": v for k, v in updates.items()}
    
    table.update_item(
        Key={'id': item_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )
    return {
        'statusCode': 200,
        'body': json.dumps('Item updated successfully')
    }
