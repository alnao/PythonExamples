"""Test di producer e consumer con una coda SQS finta (nessuna chiamata AWS)."""

import json
import os
import sys
from pathlib import Path

import pytest

os.environ["QUEUE_URL"] = "https://sqs.eu-central-1.amazonaws.com/111111111111/cdk15-Queue"
sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import consumer  # noqa: E402
import producer  # noqa: E402


class FakeSqs:
    def __init__(self):
        self.messages, self.deleted = [], []

    def send_message(self, QueueUrl, MessageBody):
        self.messages.append(MessageBody)
        return {"MessageId": f"id-{len(self.messages)}"}

    def receive_message(self, QueueUrl, MaxNumberOfMessages, WaitTimeSeconds):
        batch = self.messages[:MaxNumberOfMessages]
        return {"Messages": [{"Body": b, "ReceiptHandle": f"rh-{b}"} for b in batch]} if batch else {}

    def delete_message_batch(self, QueueUrl, Entries):
        handles = {e["ReceiptHandle"] for e in Entries}
        self.deleted += handles
        self.messages = [m for m in self.messages if f"rh-{m}" not in handles]


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    queue = FakeSqs()
    monkeypatch.setattr(producer, "sqs", lambda: queue)
    monkeypatch.setattr(consumer, "sqs", lambda: queue)
    return queue


def produce(body):
    result = producer.handler({"body": body}, None)
    return result["statusCode"], json.loads(result["body"])


def consume():
    return json.loads(consumer.handler({}, None)["body"])["messaggi"]


def test_produce_and_consume(fake):
    assert produce(json.dumps({"message": "primo"})) == (200, {"inviato": "primo", "messageId": "id-1"})
    produce(json.dumps({"message": "secondo"}))
    assert consume() == ["primo", "secondo"]
    assert fake.messages == [] and len(fake.deleted) == 2
    assert consume() == []


@pytest.mark.parametrize("body", [None, "non json", "[]", json.dumps({}), json.dumps({"message": "  "})])
def test_invalid_message(body):
    assert produce(body)[0] == 400
