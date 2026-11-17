"""Consumer: GET /consume legge fino a 10 messaggi dalla coda SQS, li cancella e li restituisce.

Long polling di 5 secondi (WaitTimeSeconds): se la coda e' vuota la risposta arriva dopo 5 secondi con una lista vuota.
"""

import json
import os

import boto3

_sqs = None


def sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs")
    return _sqs


def handler(event, context):
    queue_url = os.environ["QUEUE_URL"]
    messages = sqs().receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=5).get("Messages", [])
    for message in messages:
        print(f"messaggio ricevuto: {message['Body']}")
    if messages:
        # cancellazione in blocco: i messaggi letti non tornano visibili dopo il visibility timeout
        sqs().delete_message_batch(QueueUrl=queue_url, Entries=[
            {"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]} for i, m in enumerate(messages)])
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"messaggi": [m["Body"] for m in messages]})}
