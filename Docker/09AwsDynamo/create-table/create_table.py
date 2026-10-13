# create_table.py
import boto3
from botocore.exceptions import ClientError
import os

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT")
TABLE_NAME = os.getenv("TABLE_NAME", "alnao-persone")

# Tag standard del repository (convenzione in CLAUDE.md), usati solo su AWS reale:
# con DynamoDB Local (DYNAMODB_ENDPOINT valorizzato) la tabella si crea senza tag
STANDARD_TAGS = {
    "Name": "aws-py-Docker.09AwsDynamo",
    "Environment": "dev",
    "Project": "Development.aws.py-Docker.09AwsDynamo",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "Manual",
}

def create_table():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
        endpoint_url=DYNAMODB_ENDPOINT,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local")
    )

    extra = {}
    if not DYNAMODB_ENDPOINT:
        extra["Tags"] = [{"Key": k, "Value": v} for k, v in STANDARD_TAGS.items()]

    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "codice_fiscale", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "codice_fiscale", "AttributeType": "S"}
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            },
            **extra
        )
        table.wait_until_exists()
        print(f"Tabella '{TABLE_NAME}' creata correttamente.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"La tabella '{TABLE_NAME}' esiste già.")
        else:
            raise

if __name__ == "__main__":
    create_table()