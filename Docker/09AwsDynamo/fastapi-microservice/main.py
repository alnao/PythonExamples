from fastapi import FastAPI, HTTPException
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel
import os

app = FastAPI()
TABLE_NAME = os.getenv("TABLE_NAME", "alnao-persone")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")  # Fallback se non c'è
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "local")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "local")

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=DYNAMODB_ENDPOINT,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
table = None  # 👈 Dichiarata fuori

def initialize_dynamodb():
    global table  # 👈 Indica che usiamo la variabile globale

    TABLE_NAME = "alnao-persone"

    try:
        table = dynamodb.Table(TABLE_NAME)
        table.load()  # Verifica se esiste già
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Tabella non esiste, creala
            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'codice_fiscale', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'codice_fiscale', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            table.wait_until_exists()
        else:
            raise

class Persona(BaseModel):
    codice_fiscale: str
    nome: str
    cognome: str
    eta: int
    data_nascita: str
    
@app.on_event("startup")
def on_startup():
    initialize_dynamodb()

@app.post("/persone/")
def crea_persona(persona: Persona):
    table.put_item(Item=persona.dict())
    return {"message": "Persona creata"}

@app.get("/persone/{codice_fiscale}")
def leggi_persona(codice_fiscale: str):
    response = table.get_item(Key={"codice_fiscale": codice_fiscale})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Persona non trovata")
    return item

@app.get("/persone/")
def lista_persone():
    return table.scan()['Items']

@app.delete("/persone/{codice_fiscale}")
def elimina_persona(codice_fiscale: str):
    table.delete_item(Key={"codice_fiscale": codice_fiscale})
    return {"message": "Persona eliminata"}