import boto3
import json

def main():
    # Configura il client DynamoDB Local
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='fakeAccessKey',
        aws_secret_access_key='fakeSecretKey'
    )

    # Riferimento alla tabella
    table = dynamodb.Table('alberto-dy2')

    # Lista tutte le tabelle
    client = boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='fakeAccessKey',
        aws_secret_access_key='fakeSecretKey'
    )

    print("Tabelle disponibili:")
    tables = client.list_tables()
    print(tables['TableNames'])

    # Scan della tabella (mostra tutti gli elementi)
    print("\nContenuto della tabella alberto-dy2:")
    response = table.scan()
    for item in response['Items']:
        print(json.dumps(item, indent=2, default=str))

    # Inserisci un elemento di test
    table.put_item(
        Item={
            'id': 'test-python-123',
            'message': 'test from Python',
            'timestamp': 'test-time'
        }
    )
    print("\nElemento inserito!")

if __name__ == "__main__":
    main()
