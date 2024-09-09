import json

def handler(event, context):
    print("api",event)
    return {
        'statusCode': 200,
        'body': json.dumps('Accesso autorizzato alla risorsa protetta!')
    }