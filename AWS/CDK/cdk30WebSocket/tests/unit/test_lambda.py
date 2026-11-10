"""Test del gioco e delle Lambda con tabelle DynamoDB e WebSocket finti (nessuna chiamata AWS)."""

import copy
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import api  # noqa: E402
import aws  # noqa: E402
import game as game_module  # noqa: E402
import ws  # noqa: E402
from game import Game, GameError  # noqa: E402


def _dynamo(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, dict):
        return {k: _dynamo(v) for k, v in value.items()}
    return value


class FakeTable:
    """Quanto basta di una tabella DynamoDB: get/put/delete, scan, query sulla chiave, update_item delle espressioni usate."""

    def __init__(self, pk, sk=None):
        self.pk, self.sk, self.items = pk, sk, {}

    def _key(self, d):
        return (d[self.pk], d[self.sk]) if self.sk else d[self.pk]

    def get_item(self, Key):
        item = self.items.get(self._key(Key))
        return {"Item": copy.deepcopy(item)} if item else {}

    def put_item(self, Item):
        self.items[self._key(Item)] = _dynamo(copy.deepcopy(Item))

    def delete_item(self, Key):
        self.items.pop(self._key(Key), None)

    def scan(self, **kw):
        return {"Items": copy.deepcopy(list(self.items.values()))}

    def query(self, KeyConditionExpression, ScanIndexForward=True, Limit=None):
        name, value = KeyConditionExpression.get_expression()["values"]
        rows = sorted((i for i in self.items.values() if i[name.name] == value), key=lambda i: i[self.sk],
                      reverse=not ScanIndexForward)
        return {"Items": copy.deepcopy(rows[:Limit])}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames=None, ExpressionAttributeValues=None):
        names, values = ExpressionAttributeNames or {}, ExpressionAttributeValues or {}
        item = self.items.setdefault(self._key(Key), dict(Key))
        if UpdateExpression.startswith("REMOVE "):
            for attr in UpdateExpression[7:].split(","):
                item.pop(names.get(attr.strip(), attr.strip()), None)
            return
        for part in re.split(r",\s*(?![^()]*\))", UpdateExpression[4:]):  # virgole fuori dalle parentesi
            attr, expr = (s.strip() for s in part.split("=", 1))
            attr = names.get(attr, attr)
            m = re.fullmatch(r"if_not_exists\((\w+), (:\w+)\) ([+-]) (:\w+)", expr)
            if m:
                base = item.get(m.group(1), values[m.group(2)])
                delta = values[m.group(4)]
                item[attr] = _dynamo(int(base) + (delta if m.group(3) == "+" else -delta))
            else:
                item[attr] = _dynamo(copy.deepcopy(values[expr]))


@pytest.fixture
def setup():
    tables = SimpleNamespace(players=FakeTable("nickname"), matches=FakeTable("matchId"),
                             logs=FakeTable("day", "ts"), bans=FakeTable("nickname"))
    sent, gone = [], set()

    def send(cid, message):
        if cid in gone:
            return False
        sent.append((cid, message))
        return True
    return Game(tables, send), tables, sent, gone


def score(tables, nickname):
    return int(tables.players.items[nickname]["score"])


def test_set_number_validation(setup):
    g, *_ = setup
    for nickname, number, status in (("abc", 5, 400), ("Mario!", 5, 400), ("Mario1", 0, 400), ("Mario1", 100, 400),
                                     ("Mario1", "5", 400), ("Mario1", True, 400)):
        with pytest.raises(GameError) as e:
            g.set_number(nickname, number)
        assert e.value.status == status


def test_number_unique_and_change_limit(setup):
    g, tables, *_ = setup
    g.set_number("Alberto", 42)
    with pytest.raises(GameError) as e:
        g.set_number("Andrea", 42)
    assert e.value.status == 409
    with pytest.raises(GameError) as e:
        g.set_number("Alberto", 7)  # appena scelto: bisogna aspettare 24 ore
    assert e.value.status == 429
    tables.players.items["Alberto"]["lastUpdate"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert "cambiato" in g.set_number("Alberto", 7)
    assert int(tables.players.items["Alberto"]["number"]) == 7


def test_hit_and_miss(setup):
    g, tables, sent, _ = setup
    g.set_number("Alberto", 42)
    g.set_number("Andrea", 13)
    g.connect("Andrea", "conn-andrea")
    g.connect("Alberto", "conn-alberto")

    miss = g.guess("Alberto", 50)
    assert miss["hit"] is False and score(tables, "Alberto") == -1 and miss["left"] == 4

    with pytest.raises(GameError):
        g.guess("Alberto", 42)  # il proprio numero

    hit = g.guess("Alberto", 13)
    assert hit["hit"] is True
    assert score(tables, "Alberto") == 0 and score(tables, "Andrea") == -3
    andrea = tables.players.items["Andrea"]
    assert int(andrea["number"]) == 0
    match = next(iter(tables.matches.items.values()))
    assert (match["winner"], match["loser"], int(match["numberGuessed"])) == ("Alberto", "Andrea", 13)
    assert ("conn-andrea", "hit") in [(c, m["event"]) for c, m in sent]
    assert {c for c, m in sent if m["event"] == "match"} == {"conn-andrea", "conn-alberto"}
    # chi e' stato colpito puo' scegliere subito un nuovo numero
    assert "cambiato" in g.set_number("Andrea", 77)


def test_guess_limit_per_day(setup):
    g, *_ = setup
    g.set_number("Alberto", 42)
    for _ in range(game_module.MAX_GUESSES_PER_DAY):
        g.guess("Alberto", 1)
    with pytest.raises(GameError) as e:
        g.guess("Alberto", 1)
    assert e.value.status == 429


def test_guess_requires_registered_player(setup):
    g, *_ = setup
    with pytest.raises(GameError) as e:
        g.guess("Nessuno", 5)
    assert e.value.status == 404


def test_ban_notifies_before_delete_and_blocks(setup):
    g, tables, sent, _ = setup
    g.set_number("Cattivo1", 66)
    g.connect("Cattivo1", "conn-c")
    g.ban("Cattivo1", "spam")
    assert ("conn-c", {"event": "ban", "reason": "spam"}) in sent
    assert "Cattivo1" not in tables.players.items
    for action in (lambda: g.set_number("Cattivo1", 67), lambda: g.connect("Cattivo1", "x")):
        with pytest.raises(GameError):
            action()
    g.unban("Cattivo1")
    g.set_number("Cattivo1", 67)


def test_connect_disconnect_and_gone_connections(setup):
    g, tables, sent, gone = setup
    with pytest.raises(GameError) as e:
        g.connect("Sconosciuto", "c1")
    assert e.value.status == 404
    g.set_number("Alberto", 42)
    g.connect("Alberto", "c1")
    assert tables.players.items["Alberto"]["connectionId"] == "c1"
    gone.add("c1")  # browser chiuso senza disconnect
    g.broadcast({"event": "broadcast", "message": "ciao"})
    assert "connectionId" not in tables.players.items["Alberto"]
    g.connect("Alberto", "c2")
    g.disconnect("c2")
    assert "connectionId" not in tables.players.items["Alberto"]


def test_reset_and_cleanup(setup):
    g, tables, *_ = setup
    g.set_number("Alberto", 42)
    g.set_number("Andrea", 13)
    assert g.reset_numbers() == 2
    assert {int(p["number"]) for p in tables.players.items.values()} == {0}
    tables.players.items["Andrea"]["lastUpdate"] = (datetime.now(timezone.utc) - timedelta(days=11)).isoformat()
    assert g.cleanup_inactive() == ["Andrea"]


def test_scores_do_not_reveal_numbers(setup):
    g, *_ = setup
    g.set_number("Alberto", 42)
    scores = g.scores()
    assert scores[0]["nickname"] == "Alberto" and "number" not in scores[0]
    assert all("42" not in entry["message"] for entry in g.logs())


# ---- handler delle Lambda ----

@pytest.fixture
def handlers(setup, monkeypatch):
    g = setup[0]
    monkeypatch.setattr(aws, "game", lambda: g)
    monkeypatch.setattr(aws, "admin_key", lambda: "segreta")
    return g


def http(route, body=None, headers=None):
    result = api.handler({"routeKey": route, "body": json.dumps(body) if body is not None else None,
                          "headers": headers or {}}, None)
    return result["statusCode"], json.loads(result["body"])


def test_api_routes(handlers):
    assert http("POST /set-number", {"nickname": "Alberto", "number": 42})[0] == 200
    assert http("POST /set-number", {"nickname": "Andrea", "number": 42})[0] == 409
    status, body = http("POST /guess-number", {"attacker": "Alberto", "guess": 7})
    assert status == 200 and body["hit"] is False
    status, body = http("GET /scores")
    assert body["scores"][0] == {"nickname": "Alberto", "score": -1, "playing": True, "connected": False,
                                 "lastUpdate": body["scores"][0]["lastUpdate"]}
    assert http("GET /matches")[1] == {"matches": []}
    assert http("GET /logs")[0] == 200
    assert http("GET /nulla")[0] == 404
    assert api.handler({"routeKey": "POST /set-number", "body": "{rotto"}, None)["statusCode"] == 400


def test_admin_routes_need_key(handlers):
    assert http("POST /admin/reset")[0] == 401
    assert http("POST /admin/reset", {}, {"x-admin-key": "sbagliata"})[0] == 401
    assert http("GET /admin/bans")[0] == 401
    key = {"x-admin-key": "segreta"}
    assert http("POST /admin/ban", {"nickname": "Cattivo1", "reason": "spam"}, key)[0] == 200
    assert http("GET /admin/bans", None, key)[1]["bans"][0]["nickname"] == "Cattivo1"
    assert http("POST /admin/broadcast", {"text": ""}, key)[0] == 400
    assert http("POST /admin/broadcast", {"text": "ciao"}, key)[0] == 200
    assert http("POST /admin/reset", {}, key)[0] == 200


def test_websocket_handler(handlers):
    def event(route, cid, nickname=None, body=None):
        return {"requestContext": {"routeKey": route, "connectionId": cid},
                "queryStringParameters": {"nickname": nickname} if nickname else None, "body": body}
    assert ws.handler(event("$connect", "c1", "Alberto"), None)["statusCode"] == 404  # non iscritto
    handlers.set_number("Alberto", 42)
    assert ws.handler(event("$connect", "c1", "Alberto"), None)["statusCode"] == 200
    assert ws.handler(event("$default", "c1", body='{"action": "ping"}'), None)["statusCode"] == 200
    assert ws.handler(event("$disconnect", "c1"), None)["statusCode"] == 200
    assert ws.cleanup({}, None) == {"removed": []}
