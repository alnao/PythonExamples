"""Lambda delle route WebSocket ($connect, $disconnect, $default) e della pulizia giornaliera.

- $connect: wss://...?nickname=<nickname>, accettata solo per un giocatore iscritto e non bannato
- $disconnect: toglie il connectionId dal giocatore
- $default: {"action": "ping"} risponde {"event": "pong"} (utile per tenere viva la connessione)
"""

import json
import logging

import aws
from game import GameError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    ctx = event["requestContext"]
    route, connection_id = ctx["routeKey"], ctx["connectionId"]
    game = aws.game()
    if route == "$connect":
        nickname = (event.get("queryStringParameters") or {}).get("nickname")
        try:
            game.connect(nickname, connection_id)
        except GameError as e:
            logger.info("connessione rifiutata per %s: %s", nickname, e)
            return {"statusCode": e.status, "body": str(e)}
        return {"statusCode": 200}
    if route == "$disconnect":
        game.disconnect(connection_id)
        return {"statusCode": 200}
    try:
        message = json.loads(event.get("body") or "{}")
    except ValueError:
        message = {}
    if isinstance(message, dict) and message.get("action") == "ping":
        game.send(connection_id, {"event": "pong"})
    else:
        game.send(connection_id, {"event": "error", "message": "messaggio sconosciuto: usare {\"action\": \"ping\"}"})
    return {"statusCode": 200}


def cleanup(event, context):
    """Regola EventBridge giornaliera: toglie i giocatori inattivi."""
    removed = aws.game().cleanup_inactive()
    logger.info("giocatori inattivi tolti: %s", removed)
    return {"removed": removed}
