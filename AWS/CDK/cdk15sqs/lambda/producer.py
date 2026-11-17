"""Producer: POST /produce con body {"message": "..."} invia il messaggio alla coda SQS."""

import json
import os

import boto3

_sqs = None


def sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs")
    return _sqs


def response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"errore": "il body deve essere JSON"})
    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, str) or not message.strip():
        return response(400, {"errore": "serve il campo message (testo non vuoto)"})
    result = sqs().send_message(QueueUrl=os.environ["QUEUE_URL"], MessageBody=message)
    return response(200, {"inviato": message, "messageId": result["MessageId"]})
