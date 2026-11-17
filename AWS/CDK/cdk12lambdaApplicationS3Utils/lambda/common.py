"""Funzioni comuni alle Lambda del cdk12: client AWS, risposte API con CORS, chiave S3 dall'evento."""

import json
import os
import posixpath
from decimal import Decimal
from urllib.parse import unquote_plus

import boto3

_clients = {}


def client(name: str):
    """Client boto3 creato alla prima chiamata (i test lo sostituiscono con uno finto)."""
    if name not in _clients:
        _clients[name] = boto3.client(name)
    return _clients[name]


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"tipo non serializzabile: {type(value)}")


def response(status: int, body) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=_json_default),
    }


def query_param(event, name: str):
    return ((event or {}).get("queryStringParameters") or {}).get(name)


def s3_object(event) -> tuple:
    """Bucket e chiave dell'oggetto: evento EventBridge (Object Created) o notifica S3 (Records)."""
    if "Records" in event:
        s3 = event["Records"][0]["s3"]
        return s3["bucket"]["name"], unquote_plus(s3["object"]["key"])
    return event["detail"]["bucket"]["name"], event["detail"]["object"]["key"]


def folder(name: str) -> str:
    """Cartella del bucket dalle variabili d'ambiente (es. INPUT_FOLDER), sempre con la / finale."""
    return os.environ[name].rstrip("/") + "/"


def safe_name(path: str) -> str:
    """Percorso relativo senza parti pericolose (../, / iniziale): i file di uno zip restano nella cartella."""
    parts = [p for p in posixpath.normpath("/" + path.replace("\\", "/")).split("/") if p not in ("", ".", "..")]
    return "/".join(parts)
