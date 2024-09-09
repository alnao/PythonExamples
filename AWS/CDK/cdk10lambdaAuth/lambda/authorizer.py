import os
import jwt
from jwt.exceptions import InvalidTokenError

JWT_SECRET = os.environ['JWT_SECRET']

def handler(event, context):
    print("authorizer",event)
    try:
        # Estrai il token dalla stringa di autorizzazione
        token = event['authorizationToken'].split(' ')[-1]
        
        # Verifica il token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        # Se la verifica ha successo, genera la policy di autorizzazione
        return generate_policy('user', 'Allow', event['methodArn'])
    except InvalidTokenError:
        # Se la verifica fallisce, nega l'accesso
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id, effect, resource):
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': resource
            }]
        }
    }