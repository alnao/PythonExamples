"""Test di token JWT e Lambda in locale, senza AWS (il segreto non viene letto da Secrets Manager)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import authorizer  # noqa: E402
import jwt_hs256  # noqa: E402
import protected  # noqa: E402

SECRET = "segreto-di-prova"
METHOD_ARN = "arn:aws:execute-api:eu-central-1:111111111111:abc123/dev/GET/"


@pytest.fixture(autouse=True)
def fixed_secret(monkeypatch):
    monkeypatch.setattr(authorizer, "secret", lambda: SECRET)


def authorize(token):
    return authorizer.handler({"authorizationToken": token, "methodArn": METHOD_ARN}, None)


def test_valid_token_allowed():
    policy = authorize("Bearer " + jwt_hs256.sign({"sub": "alberto"}, SECRET))
    assert policy["principalId"] == "alberto" and policy["context"] == {"user": "alberto"}
    assert policy["policyDocument"]["Statement"][0] == {"Action": "execute-api:Invoke", "Effect": "Allow",
                                                        "Resource": METHOD_ARN}


@pytest.mark.parametrize("token", [
    "",
    "Bearer non-un-token",
    "Bearer " + jwt_hs256.sign({"sub": "alberto"}, "altro-segreto"),
    "Bearer " + jwt_hs256.sign({"sub": "alberto"}, SECRET, minutes=-1),
])
def test_invalid_tokens_unauthorized(token):
    with pytest.raises(Exception, match="^Unauthorized$"):
        authorize(token)


def test_algorithm_none_rejected():
    header = jwt_hs256._b64encode(json.dumps({"alg": "none"}).encode())
    body = jwt_hs256._b64encode(json.dumps({"sub": "x", "exp": 9999999999}).encode())
    with pytest.raises(jwt_hs256.InvalidToken, match="algoritmo"):
        jwt_hs256.verify(f"{header}.{body}.", SECRET)


def test_protected_reads_user_from_authorizer():
    response = protected.handler({"requestContext": {"authorizer": {"user": "alberto"}}}, None)
    assert response["statusCode"] == 200 and json.loads(response["body"])["utente"] == "alberto"
