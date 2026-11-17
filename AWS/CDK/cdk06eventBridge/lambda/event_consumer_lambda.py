"""Lambda invocata da EventBridge: file caricati nel bucket (Object Created) ed esecuzione schedulata.

Ispirata all'esempio aws-samples api-eventbridge-lambda:
https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-eventbridge-lambda/lambda/event_consumer_lambda.py
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def describe(event: dict) -> dict:
    """Riassunto dell'evento: file caricato (con bucket, chiave e dimensione) oppure esecuzione schedulata."""
    if event.get("source") == "aws.s3" and event.get("detail-type") == "Object Created":
        detail = event["detail"]
        return {"tipo": "file", "bucket": detail["bucket"]["name"], "chiave": detail["object"]["key"],
                "dimensione": detail["object"].get("size")}
    if event.get("detail-type") == "Scheduled Event":
        return {"tipo": "schedulata", "orario": event.get("time")}
    return {"tipo": "sconosciuto", "source": event.get("source")}


def lambda_handler(event, context):
    logger.info("evento ricevuto: %s", json.dumps(event))
    summary = describe(event)
    logger.info("riassunto: %s", json.dumps(summary))
    return {"statusCode": 200, "body": json.dumps(summary)}
