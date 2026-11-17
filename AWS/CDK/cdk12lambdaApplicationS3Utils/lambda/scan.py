"""Lambda schedulata (ogni giorno alle 01:00 UTC): elenca tutti i file del bucket e aggiorna la tabella della scansione.

- file mai visto: nuova riga con nuovo=S (id = sha256 di percorso e nome)
- file gia' presente: nuovo=N e data di aggiornamento della riga
"""

import hashlib
import os
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from common import client


def file_id(path: str, name: str) -> str:
    return hashlib.sha256(f"{path}/{name}".encode()).hexdigest()


def scan_bucket(event, context):
    now = datetime.now(timezone.utc).isoformat()
    table = os.environ["SCAN_TABLE"]
    dynamodb = client("dynamodb")
    new, known = 0, 0
    for page in client("s3").get_paginator("list_objects_v2").paginate(Bucket=os.environ["BUCKET_NAME"]):
        for obj in page.get("Contents", []):
            path, _, name = obj["Key"].rpartition("/")
            if not name:  # "cartelle" vuote create dalla console
                continue
            item_id = file_id(path, name)
            try:
                dynamodb.put_item(TableName=table, ConditionExpression="attribute_not_exists(id)", Item={
                    "id": {"S": item_id}, "nomeFile": {"S": name}, "path": {"S": path},
                    "dimensione": {"N": str(obj["Size"])}, "dataOraCreazioneFile": {"S": obj["LastModified"].isoformat()},
                    "nuovo": {"S": "S"}, "dataOraAggiornamentoRiga": {"S": now}})
                new += 1
            except ClientError as e:
                if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
                dynamodb.update_item(TableName=table, Key={"id": {"S": item_id}},
                                     UpdateExpression="SET nuovo = :n, dataOraAggiornamentoRiga = :d",
                                     ExpressionAttributeValues={":n": {"S": "N"}, ":d": {"S": now}})
                known += 1
    print(f"scansione completata: {new} file nuovi, {known} gia' presenti")
    return {"nuovi": new, "gia_presenti": known}
