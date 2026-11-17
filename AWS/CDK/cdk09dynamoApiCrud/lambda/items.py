"""CRUD degli item della tabella DynamoDB, un handler per ogni Lambda dell'API.

- POST   /items        create: crea un item (id generato se manca), 201; 409 se l'id esiste gia'
- GET    /items        read:   lista di tutti gli item (scan con paginazione)
- GET    /items/{id}   read:   un item, 404 se non esiste
- PUT    /items/{id}   update: aggiorna i campi indicati (non l'id), 404 se l'item non esiste
- DELETE /items/{id}   delete: cancella l'item, 404 se non esiste

I numeri del body JSON diventano Decimal (DynamoDB non accetta i float) e tornano numeri nella risposta.
"""

import json
import os
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

_table = None


def table():
    """Tabella DynamoDB, creata alla prima chiamata (i test la sostituiscono con una finta)."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


class BadRequest(Exception):
    pass


def _to_json(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"tipo non serializzabile: {type(value)}")


def response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, default=_to_json)}


def parse_body(event) -> dict:
    try:
        body = json.loads(event.get("body") or "", parse_float=Decimal)
    except json.JSONDecodeError:
        raise BadRequest("il body deve essere un oggetto JSON")
    if not isinstance(body, dict) or not body:
        raise BadRequest("il body deve essere un oggetto JSON non vuoto")
    return body


def item_id(event) -> str:
    return (event.get("pathParameters") or {}).get("id")


def handle(missing_status: int = 404, missing_message: str = "item non trovato"):
    """Errori di validazione -> 400; condizione DynamoDB non rispettata -> missing_status (404, o 409 per create)."""
    def decorator(fn):
        def wrapper(event, context):
            try:
                return fn(event or {})
            except BadRequest as e:
                return response(400, {"errore": str(e)})
            except ClientError as e:
                if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    return response(missing_status, {"errore": missing_message})
                raise
        return wrapper
    return decorator


@handle(409, "item gia' presente")
def create(event):
    item = parse_body(event)
    item["id"] = str(item.get("id") or uuid.uuid4())
    table().put_item(Item=item, ConditionExpression="attribute_not_exists(id)")
    return response(201, item)


@handle()
def read(event):
    if item_id(event):
        item = table().get_item(Key={"id": item_id(event)}).get("Item")
        return response(200, item) if item else response(404, {"errore": "item non trovato"})
    items, kwargs = [], {}
    while True:
        page = table().scan(**kwargs)
        items += page.get("Items", [])
        if "LastEvaluatedKey" not in page:
            return response(200, items)
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


@handle()
def update(event):
    updates = parse_body(event)
    updates.pop("id", None)  # la chiave non si modifica
    if not updates:
        raise BadRequest("nessun campo da aggiornare")
    names = {f"#f{i}": k for i, k in enumerate(updates)}
    values = {f":v{i}": v for i, v in enumerate(updates.values())}
    result = table().update_item(
        Key={"id": item_id(event)},
        UpdateExpression="SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(updates))),
        ConditionExpression="attribute_exists(id)",
        ExpressionAttributeNames=names, ExpressionAttributeValues=values, ReturnValues="ALL_NEW")
    return response(200, result["Attributes"])


@handle()
def delete(event):
    table().delete_item(Key={"id": item_id(event)}, ConditionExpression="attribute_exists(id)")
    return response(200, {"cancellato": item_id(event)})
