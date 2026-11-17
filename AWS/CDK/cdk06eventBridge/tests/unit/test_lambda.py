"""Test del codice della Lambda in locale, senza AWS."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import event_consumer_lambda  # noqa: E402

S3_EVENT = {
    "source": "aws.s3", "detail-type": "Object Created",
    "detail": {"bucket": {"name": "bucket-cdk06"}, "object": {"key": "INPUT/prova.md", "size": 42}},
}
SCHEDULED_EVENT = {"source": "aws.events", "detail-type": "Scheduled Event", "time": "2026-11-17T18:00:00Z"}


def test_object_created():
    body = json.loads(event_consumer_lambda.lambda_handler(S3_EVENT, None)["body"])
    assert body == {"tipo": "file", "bucket": "bucket-cdk06", "chiave": "INPUT/prova.md", "dimensione": 42}


def test_scheduled_event():
    assert event_consumer_lambda.describe(SCHEDULED_EVENT) == {"tipo": "schedulata", "orario": "2026-11-17T18:00:00Z"}


def test_unknown_event():
    assert event_consumer_lambda.describe({"source": "altro"})["tipo"] == "sconosciuto"
