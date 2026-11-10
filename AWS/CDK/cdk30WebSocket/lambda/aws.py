"""Collegamento del gioco ad AWS: tabelle DynamoDB, invio dei messaggi WebSocket, chiave di amministrazione."""

import json
import logging
import os
from types import SimpleNamespace

import boto3
from botocore.exceptions import ClientError

from game import Game

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_game = None
_admin_key = None
_ws_client = None


def _send(connection_id: str, message: dict) -> bool:
    """post_to_connection sull'endpoint di gestione dello stage WebSocket; False se il client se n'e' andato."""
    global _ws_client
    if _ws_client is None:
        _ws_client = boto3.client("apigatewaymanagementapi", endpoint_url=os.environ["WS_ENDPOINT"])
    try:
        _ws_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(message, default=str).encode())
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "GoneException":
            return False
        logger.warning("invio a %s fallito: %s", connection_id, e)
        return True


def game() -> Game:
    global _game
    if _game is None:
        db = boto3.resource("dynamodb")
        tables = SimpleNamespace(**{name: db.Table(os.environ[f"{name.upper()}_TABLE"])
                                    for name in ("players", "matches", "logs", "bans")})
        _game = Game(tables, _send)
    return _game


def admin_key() -> str:
    """Chiave di amministrazione in Secrets Manager, letta una volta per istanza della Lambda."""
    global _admin_key
    if _admin_key is None:
        sm = boto3.client("secretsmanager")
        _admin_key = sm.get_secret_value(SecretId=os.environ["ADMIN_SECRET_ARN"])["SecretString"]
    return _admin_key
