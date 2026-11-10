"""Lambda delle API HTTP del gioco (API Gateway HTTP API, evento formato 2.0).

Gioco:            POST /set-number {nickname, number}   POST /guess-number {attacker, guess}
Letture:          GET /scores   GET /matches   GET /logs
Amministrazione:  POST /admin/ban {nickname, reason}   POST /admin/unban {nickname}   GET /admin/bans
(header X-Admin-Key) POST /admin/broadcast {text}      POST /admin/reset
"""

import hmac
import json
import logging

import aws
from game import GameError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, default=lambda v: int(v) if v == int(v) else float(v))}


def _admin(event) -> bool:
    key = (event.get("headers") or {}).get("x-admin-key", "")
    return bool(key) and hmac.compare_digest(key, aws.admin_key())


def handler(event, context):
    route = event.get("routeKey", "")
    try:
        body = json.loads(event.get("body") or "{}") if event.get("body") else {}
        if not isinstance(body, dict):
            raise ValueError
    except ValueError:
        return response(400, {"error": "body JSON non valido"})

    game = aws.game()
    try:
        if route.startswith("POST /admin/") or route == "GET /admin/bans":
            if not _admin(event):
                return response(401, {"error": "chiave di amministrazione mancante o errata"})
        if route == "POST /set-number":
            return response(200, {"message": game.set_number(body.get("nickname"), body.get("number"))})
        if route == "POST /guess-number":
            return response(200, game.guess(body.get("attacker"), body.get("guess")))
        if route == "GET /scores":
            return response(200, {"scores": game.scores()})
        if route == "GET /matches":
            return response(200, {"matches": game.matches()})
        if route == "GET /logs":
            return response(200, {"logs": game.logs()})
        if route == "POST /admin/ban":
            return response(200, {"message": game.ban(body.get("nickname"), body.get("reason"))})
        if route == "POST /admin/unban":
            return response(200, {"message": game.unban(body.get("nickname"))})
        if route == "GET /admin/bans":
            return response(200, {"bans": game.bans()})
        if route == "POST /admin/broadcast":
            text = str(body.get("text", "")).strip()[:500]
            if not text:
                return response(400, {"error": "testo del messaggio mancante"})
            sent = game.broadcast({"event": "broadcast", "message": text})
            game.log("admin", f"messaggio a tutti: {text}")
            return response(200, {"message": f"messaggio inviato a {sent} giocatori collegati"})
        if route == "POST /admin/reset":
            return response(200, {"message": f"numeri azzerati per {game.reset_numbers()} giocatori"})
        return response(404, {"error": f"percorso sconosciuto: {route}"})
    except GameError as e:
        return response(e.status, {"error": str(e)})
