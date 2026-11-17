"""Lambda authorizer (tipo TOKEN) di API Gateway: verifica il token JWT dell'header Authorization.

- token valido: policy Allow sul metodo chiamato, con l'utente (claim "sub") nel contesto
- token mancante, scaduto o con firma sbagliata: eccezione "Unauthorized", API Gateway risponde 401
Il segreto HS256 e' letto da Secrets Manager (JWT_SECRET_ARN) alla prima chiamata e tenuto in memoria.
"""

import os

import boto3

from jwt_hs256 import InvalidToken, verify

_secret = None


def secret() -> str:
    global _secret
    if _secret is None:
        client = boto3.client("secretsmanager")
        _secret = client.get_secret_value(SecretId=os.environ["JWT_SECRET_ARN"])["SecretString"]
    return _secret


def generate_policy(principal_id: str, effect: str, resource: str, context: dict = None) -> dict:
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}],
        },
    }
    if context:
        policy["context"] = context
    return policy


def handler(event, context):
    token = (event.get("authorizationToken") or "").removeprefix("Bearer ").strip()
    try:
        payload = verify(token, secret())
    except InvalidToken as e:
        print(f"accesso negato: {e}")
        raise Exception("Unauthorized")  # messaggio fisso: API Gateway risponde 401
    user = str(payload.get("sub", "anonimo"))
    return generate_policy(user, "Allow", event["methodArn"], {"user": user})
