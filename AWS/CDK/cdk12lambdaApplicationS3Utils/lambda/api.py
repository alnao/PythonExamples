"""Lambda delle API GET (una funzione per ogni percorso, stesso codice).

- upload_zip          /upload-zip?file_name=x.zip   URL prefirmato (PUT, 1 ora) per caricare lo zip in INPUT/
- list_excel_files    /list-excel-files             file Excel in DEZIPPED/
- download_excel_file /download-excel-file?file_key=DEZIPPED/x.xlsx   URL prefirmato (GET, 1 ora)
- read_dynamodb_data  /read-dynamodb-data           righe di log dei caricamenti, dalla piu' recente
- list_new_files      /list-new-files               file con nuovo=S nella tabella della scansione
- find_file           /find-file?nomeFile=x         percorsi in cui si trova un file con quel nome
"""

import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

from common import client, folder, query_param, response, safe_name

EXCEL = (".xlsx", ".xls")
_dynamodb = None


def table(name_env: str):
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(os.environ[name_env])


def presigned_s3():
    """Client S3 con firma v4 e endpoint della region: gli URL prefirmati funzionano subito anche per bucket nuovi."""
    region = os.environ.get("AWS_REGION")
    return boto3.client("s3", region_name=region, config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))


def upload_zip(event, context):
    file_name = safe_name(query_param(event, "file_name") or "").split("/")[-1]
    if not file_name:
        return response(400, {"error": "manca il parametro file_name"})
    if not file_name.lower().endswith(".zip"):
        return response(400, {"error": "il file deve avere estensione .zip"})
    key = folder("INPUT_FOLDER") + file_name
    url = presigned_s3().generate_presigned_url("put_object", ExpiresIn=3600,
                                                Params={"Bucket": os.environ["BUCKET_NAME"], "Key": key})
    return response(200, {"upload_url": url, "key": key})


def list_excel_files(event, context):
    files = []
    paginator = client("s3").get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=os.environ["BUCKET_NAME"], Prefix=folder("DEZIPPED_FOLDER")):
        for obj in page.get("Contents", []):
            if obj["Key"].lower().endswith(EXCEL):
                files.append({"key": obj["Key"], "name": os.path.basename(obj["Key"]), "size": obj["Size"],
                              "last_modified": obj["LastModified"]})
    return response(200, files)


def download_excel_file(event, context):
    key = query_param(event, "file_key") or ""
    # solo i file Excel della cartella DEZIPPED: l'API non deve aprire tutto il bucket
    if not key.startswith(folder("DEZIPPED_FOLDER")) or safe_name(key) != key or not key.lower().endswith(EXCEL):
        return response(400, {"error": "file_key deve essere un file Excel della cartella " + folder("DEZIPPED_FOLDER")})
    url = presigned_s3().generate_presigned_url("get_object", ExpiresIn=3600,
                                                Params={"Bucket": os.environ["BUCKET_NAME"], "Key": key})
    return response(200, {"download_url": url})


def read_dynamodb_data(event, context):
    log, items, kwargs = table("LOG_TABLE"), [], {}
    while True:
        page = log.scan(**kwargs)
        items += page.get("Items", [])
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    items.sort(key=lambda i: i.get("data_caricamento", ""), reverse=True)
    return response(200, items)


def list_new_files(event, context):
    items = table("SCAN_TABLE").query(IndexName="nuovo-index", KeyConditionExpression=Key("nuovo").eq("S"))["Items"]
    return response(200, items)


def find_file(event, context):
    name = query_param(event, "nomeFile")
    if not name:
        return response(400, {"error": "manca il parametro nomeFile"})
    items = table("SCAN_TABLE").query(IndexName="nomeFile-index", KeyConditionExpression=Key("nomeFile").eq(name))["Items"]
    return response(200, items)
