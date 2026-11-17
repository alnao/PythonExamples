"""Test della Lambda iscritta al topic, in locale."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import index  # noqa: E402


def test_logs_every_record():
    event = {"Records": [
        {"Sns": {"MessageId": "1", "Subject": "cdk16: prova", "Message": "primo"}},
        {"Sns": {"MessageId": "2", "Subject": None, "Message": "secondo"}},
    ]}
    result = index.handler(event, None)
    assert result["ricevuti"] == 2
    assert [m["message"] for m in result["messaggi"]] == ["primo", "secondo"]


def test_empty_event():
    assert index.handler({}, None) == {"ricevuti": 0, "messaggi": []}
