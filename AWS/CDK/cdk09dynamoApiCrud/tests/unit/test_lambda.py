"""Test delle Lambda CRUD con una tabella DynamoDB finta (nessuna chiamata AWS)."""

import copy
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ["TABLE_NAME"] = "items"
sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import items  # noqa: E402


def conditional_failed(operation):
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, operation)


class FakeTable:
    """Le operazioni usate da items.py; come DynamoDB rifiuta i float e restituisce i numeri come Decimal."""

    def __init__(self):
        self.items = {}

    @staticmethod
    def _check(value):
        if isinstance(value, float):
            raise TypeError("Float types are not supported. Use Decimal types instead.")
        for v in value.values() if isinstance(value, dict) else value if isinstance(value, list) else []:
            FakeTable._check(v)

    def put_item(self, Item, ConditionExpression=None):
        self._check(Item)
        if ConditionExpression and Item["id"] in self.items:
            raise conditional_failed("PutItem")
        self.items[Item["id"]] = copy.deepcopy(Item)

    def get_item(self, Key):
        item = self.items.get(Key["id"])
        return {"Item": copy.deepcopy(item)} if item else {}

    def scan(self, ExclusiveStartKey=None):
        rows = sorted(self.items.values(), key=lambda i: i["id"])
        if ExclusiveStartKey:
            rows = [r for r in rows if r["id"] > ExclusiveStartKey["id"]]
        page = rows[:2]  # pagine da 2 per provare la paginazione
        result = {"Items": copy.deepcopy(page)}
        if len(rows) > 2:
            result["LastEvaluatedKey"] = {"id": page[-1]["id"]}
        return result

    def update_item(self, Key, UpdateExpression, ConditionExpression, ExpressionAttributeNames,
                    ExpressionAttributeValues, ReturnValues):
        self._check(ExpressionAttributeValues)
        if Key["id"] not in self.items:
            raise conditional_failed("UpdateItem")
        for assignment in UpdateExpression.removeprefix("SET ").split(", "):
            name, value = assignment.split(" = ")
            self.items[Key["id"]][ExpressionAttributeNames[name]] = ExpressionAttributeValues[value]
        return {"Attributes": copy.deepcopy(self.items[Key["id"]])}

    def delete_item(self, Key, ConditionExpression):
        if Key["id"] not in self.items:
            raise conditional_failed("DeleteItem")
        del self.items[Key["id"]]


@pytest.fixture(autouse=True)
def table(monkeypatch):
    fake = FakeTable()
    monkeypatch.setattr(items, "table", lambda: fake)
    return fake


def call(handler, body=None, item_id=None):
    event = {"body": json.dumps(body) if isinstance(body, dict) else body,
             "pathParameters": {"id": item_id} if item_id else None}
    result = handler(event, None)
    return result["statusCode"], json.loads(result["body"])


def test_full_crud():
    status, created = call(items.create, {"id": "1", "name": "Alberto", "price": 9.99, "qty": 3})
    assert status == 201 and created == {"id": "1", "name": "Alberto", "price": 9.99, "qty": 3}
    assert call(items.read, item_id="1") == (200, created)  # numeri tornano numeri (non Decimal)
    status, updated = call(items.update, {"description": "magnifico", "price": 12.5}, item_id="1")
    assert status == 200 and updated["description"] == "magnifico" and updated["price"] == 12.5
    assert call(items.delete, item_id="1") == (200, {"cancellato": "1"})
    assert call(items.read, item_id="1")[0] == 404


def test_numbers_stored_as_decimal(table):
    call(items.create, {"id": "1", "price": 9.99})
    assert table.items["1"]["price"] == Decimal("9.99")


def test_generated_id():
    status, created = call(items.create, {"name": "senza id"})
    assert status == 201 and len(created["id"]) == 36


def test_duplicate_id():
    call(items.create, {"id": "1"})
    assert call(items.create, {"id": "1"})[0] == 409


def test_list_with_pagination():
    for i in range(5):
        call(items.create, {"id": str(i)})
    status, rows = call(items.read)
    assert status == 200 and [r["id"] for r in rows] == ["0", "1", "2", "3", "4"]


@pytest.mark.parametrize("body", [None, "", "non json", "[1, 2]", "{}"])
def test_invalid_body(body):
    assert call(items.create, body)[0] == 400


def test_update_cannot_change_id_and_needs_fields():
    call(items.create, {"id": "1"})
    assert call(items.update, {"id": "2"}, item_id="1")[0] == 400
    assert call(items.update, {"a": 1}, item_id="99")[0] == 404


def test_delete_missing():
    assert call(items.delete, item_id="99")[0] == 404
