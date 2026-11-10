"""Test della blockchain e delle Lambda con tabelle DynamoDB finte (nessuna chiamata AWS)."""

import copy
import json
import os
import sys
from decimal import Decimal

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.update(BLOCKS_TABLE="blocks", TRANSACTIONS_TABLE="transactions", DIFFICULTY="3")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import api  # noqa: E402
import chain  # noqa: E402


def _dynamo(value):
    """Come DynamoDB: i numeri tornano Decimal."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dynamo(v) for v in value]
    return value


class FakeTable:
    def __init__(self, pk, sk):
        self.pk, self.sk, self.items = pk, sk, {}

    def _key(self, item):
        return (item[self.pk], item[self.sk])

    def put_item(self, Item, ConditionExpression=None, ExpressionAttributeNames=None):
        if ConditionExpression and self._key(Item) in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[self._key(Item)] = _dynamo(copy.deepcopy(Item))

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues):
        item = self.items[(Key[self.pk], Key[self.sk])]
        item["status"] = ExpressionAttributeValues[":mined"]
        item["block_index"] = _dynamo(ExpressionAttributeValues[":index"])

    def query(self, KeyConditionExpression, IndexName=None, ScanIndexForward=True, Limit=None, **kw):
        name, value = (v for v in KeyConditionExpression.get_expression()["values"])
        rows = [i for i in self.items.values() if i.get(name.name) == value]
        rows.sort(key=lambda i: i[self.sk] if IndexName is None else i["timestamp"], reverse=not ScanIndexForward)
        return {"Items": copy.deepcopy(rows[:Limit] if Limit else rows)}

    def scan(self, **kw):
        return {"Items": copy.deepcopy(list(self.items.values()))}


@pytest.fixture
def db(monkeypatch):
    blocks, transactions = FakeTable("chain", "index"), FakeTable("sender", "timestamp")
    monkeypatch.setattr(api, "tables", lambda: (blocks, transactions))
    return blocks, transactions


def body(result):
    return json.loads(result["body"])


def post_tx(sender, recipient, amount):
    return api.add_transaction({"body": json.dumps({"sender": sender, "recipient": recipient, "amount": amount})}, None)


# ---- chain.py ----

def test_mine_respects_difficulty_and_validates():
    txs = [{"id": "1", "sender": "a", "recipient": "b", "amount": Decimal("2.5"), "timestamp": "t1", "status": "pending"}]
    block = chain.mine(0, txs, chain.GENESIS_PREVIOUS_HASH, 1700000000, 3)
    assert block["hash"].startswith("000")
    assert "status" not in block["transactions"][0]
    assert chain.validate([block]) == []


def test_validate_detects_tampering():
    b0 = chain.mine(0, [{"id": "1", "sender": "a", "recipient": "b", "amount": 5, "timestamp": "t1"}], chain.GENESIS_PREVIOUS_HASH, 1, 2)
    b1 = chain.mine(1, [{"id": "2", "sender": "b", "recipient": "c", "amount": 1, "timestamp": "t2"}], b0["hash"], 2, 2)
    assert chain.validate([b0, b1]) == []
    tampered = copy.deepcopy(b0)
    tampered["transactions"][0]["amount"] = 500
    errors = chain.validate([tampered, b1])
    assert any("tx_root" in e for e in errors)
    broken_link = copy.deepcopy(b1)
    broken_link["previous_hash"] = "f" * 64
    assert any("previous_hash" in e for e in chain.validate([b0, broken_link]))


def test_hash_same_after_dynamodb_round_trip():
    """I numeri letti da DynamoDB sono Decimal: l'hash ricalcolato deve restare uguale."""
    block = chain.mine(0, [{"id": "1", "sender": "a", "recipient": "b", "amount": Decimal("1.50"), "timestamp": "t"}],
                       chain.GENESIS_PREVIOUS_HASH, 1700000000, 2)
    assert chain.validate([_dynamo(block)]) == []


def test_balances():
    txs = [{"sender": "Root", "recipient": "Nao", "amount": Decimal("100")},
           {"sender": "Nao", "recipient": "Alice", "amount": Decimal("30.5")}]
    assert chain.balances(txs) == {"Root": Decimal("-100"), "Nao": Decimal("69.5"), "Alice": Decimal("30.5")}


# ---- api.py ----

@pytest.mark.parametrize("payload", [
    {"sender": "a", "recipient": "b", "amount": -1},
    {"sender": "a", "recipient": "b", "amount": "abc"},
    {"sender": "a", "recipient": "a", "amount": 1},
    {"sender": "", "recipient": "b", "amount": 1},
    {"sender": "a", "recipient": "b", "amount": 0.000000001},
])
def test_add_transaction_rejects_invalid(db, payload):
    assert api.add_transaction({"body": json.dumps(payload)}, None)["statusCode"] == 400


def test_add_transaction_rejects_non_object_body(db):
    assert api.add_transaction({"body": "[1, 2]"}, None)["statusCode"] == 400


def test_full_flow(db):
    blocks, transactions = db
    assert body(api.mine_block({}, None))["message"] == "nessuna transazione in attesa"

    assert post_tx("Root", "Nao", 1984)["statusCode"] == 201
    assert post_tx("Nao", "Alice", 50)["statusCode"] == 201
    first = api.mine_block({}, None)
    assert first["statusCode"] == 201
    b0 = body(first)["block"]
    assert b0["index"] == 0 and b0["hash"].startswith("000") and len(b0["transactions"]) == 2

    post_tx("Nao", "Vale", 42)
    b1 = body(api.mine_block({}, None))["block"]
    assert b1["index"] == 1 and b1["previous_hash"] == b0["hash"] and len(b1["transactions"]) == 1

    txs = body(api.get_transactions({}, None))["transactions"]
    assert {t["status"] for t in txs} == {"mined"}
    assert sorted(t["block_index"] for t in txs) == [0, 0, 1]

    assert body(api.get_balances({}, None))["balances"] == {"Root": -1984, "Nao": 1892, "Alice": 50, "Vale": 42}
    assert len(body(api.get_blocks({}, None))["blocks"]) == 2
    assert body(api.validate_chain({}, None)) == {"valid": True, "blocks": 2, "errors": []}


def test_tampered_block_is_reported(db):
    blocks, _ = db
    post_tx("Root", "Nao", 10)
    api.mine_block({}, None)
    stored = next(iter(blocks.items.values()))
    stored["transactions"][0]["amount"] = Decimal("1000")
    result = body(api.validate_chain({}, None))
    assert result["valid"] is False and result["errors"]


def test_concurrent_mining_conflict(db, monkeypatch):
    """Se un altro mining scrive lo stesso indice prima, la risposta e' 409 e le transazioni restano pending."""
    blocks, transactions = db
    post_tx("Root", "Nao", 10)
    real_put = blocks.put_item

    def put_after_other_miner(Item, **kw):
        real_put({"chain": "main", "index": Item["index"], "hash": "x"})
        return real_put(Item, **kw)
    monkeypatch.setattr(blocks, "put_item", put_after_other_miner)
    assert api.mine_block({}, None)["statusCode"] == 409
    assert {t["status"] for t in transactions.items.values()} == {"pending"}
