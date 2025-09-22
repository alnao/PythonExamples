# questo script verifica se il modello di embedding Titan embed è accessibile
# eseguirlo da terminale con: python check_model.py 
# assicurarsi di avere le variabili d'ambiente AWS configurate

import boto3
import json
bedrock = boto3.client('bedrock-runtime', region_name='eu-central-1')
try:
    body = json.dumps({'inputText': 'Hello world'})  # Titan embed expects string input
    resp = bedrock.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        body=body,
        contentType='application/json',
        accept='application/json'
    )
    print('✅ Titan embed model accessible')
    print(resp['ResponseMetadata']['HTTPStatusCode'])
    print(resp['ResponseMetadata'])
except Exception as e:
    print('❌ Error:', str(e))