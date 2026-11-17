"""Test del codice della Lambda in locale, senza AWS."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import function  # noqa: E402

CONTEXT = SimpleNamespace(invoked_function_arn="arn:aws:lambda:eu-central-1:111111111111:function:cdk08-StageInfo:prod")


def test_stage_and_alias():
    response = function.handler({"stageVariables": {"lambdaAlias": "prod"}}, CONTEXT)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["apiStage"] == "prod" and body["lambdaAlias"] == "prod"


def test_without_stage_variables():
    assert function.handler({"stageVariables": None}, CONTEXT)["statusCode"] == 404
    assert function.handler({}, CONTEXT)["statusCode"] == 404
