"""Test del codice della Lambda in locale, senza AWS."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import cdk05lambda_code  # noqa: E402


def test_greets_the_name_in_the_event():
    response = cdk05lambda_code.lambda_handler({"nome": "Alberto"}, SimpleNamespace(aws_request_id="req-1"))
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"messaggio": "Ciao Alberto!", "requestId": "req-1"}


def test_default_name_from_environment(monkeypatch):
    monkeypatch.setenv("DEFAULT_NAME", "AlNao")
    body = json.loads(cdk05lambda_code.lambda_handler({}, None)["body"])
    assert body["messaggio"] == "Ciao AlNao!"
