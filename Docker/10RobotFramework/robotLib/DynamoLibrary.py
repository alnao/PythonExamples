import boto3
from botocore.exceptions import ClientError
from robot.api.deco import keyword

class DynamoLibrary:
    def __init__(self, endpoint_url='http://localhost:8000', region='us-east-1'):
        #self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url , region_name='us-east-1')
        self.dynamodb = boto3.resource('dynamodb',endpoint_url=endpoint_url,region_name=region,aws_access_key_id='fakeAccessKey',aws_secret_access_key='fakeSecretKey')
    
    @keyword("Get Item By Id")
    def get_item_by_id(self, table_name, item_id):
        table = self.dynamodb.Table(table_name)
        try:
            response = table.get_item(Key={'id': item_id})
            return response.get('Item', None)
        except ClientError as e:
            print(f"Errore DynamoDB: {e.response['Error']['Message']}")
            return None
        except Exception as e:
            print(f"Errore generico: {str(e)}")
            return None