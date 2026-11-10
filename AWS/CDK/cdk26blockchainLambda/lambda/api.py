"""Lambda della blockchain dietro API Gateway REST: una funzione per ogni operazione, stesso codice.

- add_transaction  POST /transaction   transazione in attesa (status=pending)
- mine_block       POST /mine          nuovo blocco con le transazioni in attesa (proof of work)
- get_transactions GET  /transactions  tutte le transazioni, con stato e blocco
- get_balances     GET  /balances      saldo di ogni indirizzo dalle transazioni minate
- get_blocks       GET  /blocks        la catena, blocco per blocco
- validate_chain   GET  /validate      ricalcola gli hash e controlla i collegamenti

Tabelle: BLOCKS_TABLE (chiave chain="main" + index) e TRANSACTIONS_TABLE (sender + timestamp,
indice StatusIndex su status + timestamp).
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import chain

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CHAIN_ID = "main"
DIFFICULTY = int(os.environ.get("DIFFICULTY", "4"))
MAX_TX_PER_BLOCK = int(os.environ.get("MAX_TX_PER_BLOCK", "50"))
MAX_AMOUNT = Decimal("1000000")

_dynamodb = None


def tables():
    """Tabelle DynamoDB (create alla prima chiamata, sostituibili nei test)."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(os.environ["BLOCKS_TABLE"]), _dynamodb.Table(os.environ["TRANSACTIONS_TABLE"])


def response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(chain._plain(body)),
    }


def _query_all(table, **kwargs) -> list:
    items = []
    while True:
        page = table.query(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _scan_all(table) -> list:
    items, kwargs = [], {}
    while True:
        page = table.scan(**kwargs)
        items.extend(page.get("Items", []))
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def _by_status(transactions_table, status: str) -> list:
    return _query_all(transactions_table, IndexName="StatusIndex",
                      KeyConditionExpression=Key("status").eq(status))


def add_transaction(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        if not isinstance(body, dict):
            raise ValueError("il body deve essere un oggetto JSON")
        sender, recipient = str(body.get("sender", "")).strip(), str(body.get("recipient", "")).strip()
        amount = Decimal(str(body.get("amount")))
    except (ValueError, InvalidOperation):
        return response(400, {"error": "body JSON non valido: servono sender, recipient e amount"})
    if not sender or not recipient or len(sender) > 64 or len(recipient) > 64:
        return response(400, {"error": "sender e recipient obbligatori (al massimo 64 caratteri)"})
    if sender == recipient:
        return response(400, {"error": "sender e recipient devono essere diversi"})
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT or amount.as_tuple().exponent < -8:
        return response(400, {"error": f"amount deve essere un numero positivo fino a {MAX_AMOUNT} (al massimo 8 decimali)"})

    _, transactions_table = tables()
    tx = {
        "id": uuid.uuid4().hex,
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }
    transactions_table.put_item(Item=tx)
    logger.info("transazione %s: %s -> %s %s", tx["id"], sender, recipient, amount)
    return response(201, {"message": "transazione aggiunta, in attesa del mining", "transaction": tx})


def last_block(blocks_table):
    page = blocks_table.query(KeyConditionExpression=Key("chain").eq(CHAIN_ID), ScanIndexForward=False, Limit=1)
    items = page.get("Items", [])
    return items[0] if items else None


def mine_block(event, context):
    blocks_table, transactions_table = tables()
    pending = sorted(_by_status(transactions_table, "pending"), key=lambda tx: tx["timestamp"])[:MAX_TX_PER_BLOCK]
    if not pending:
        return response(200, {"message": "nessuna transazione in attesa"})

    previous = last_block(blocks_table)
    index = int(previous["index"]) + 1 if previous else 0
    previous_hash = previous["hash"] if previous else chain.GENESIS_PREVIOUS_HASH
    started = time.time()
    block = chain.mine(index, pending, previous_hash, int(started), DIFFICULTY)
    logger.info("blocco %s: nonce %s in %.2f s, hash %s", index, block["nonce"], time.time() - started, block["hash"])

    try:
        # un altro mining nello stesso momento avrebbe lo stesso indice: vince il primo che scrive
        blocks_table.put_item(Item={"chain": CHAIN_ID, **block},
                              ConditionExpression="attribute_not_exists(#i)", ExpressionAttributeNames={"#i": "index"})
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(409, {"error": f"il blocco {index} e' stato appena minato da un'altra richiesta: riprovare"})
        raise

    for tx in pending:
        transactions_table.update_item(
            Key={"sender": tx["sender"], "timestamp": tx["timestamp"]},
            UpdateExpression="SET #s = :mined, block_index = :index",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":mined": "mined", ":index": index})
    return response(201, {"message": f"blocco {index} minato", "seconds": round(time.time() - started, 3), "block": block})


def get_transactions(event, context):
    _, transactions_table = tables()
    items = sorted(_scan_all(transactions_table), key=lambda tx: tx["timestamp"])
    return response(200, {"transactions": items})


def get_balances(event, context):
    _, transactions_table = tables()
    mined = _by_status(transactions_table, "mined")
    return response(200, {"balances": chain.balances(mined), "transactions": len(mined)})


def _all_blocks(blocks_table) -> list:
    return _query_all(blocks_table, KeyConditionExpression=Key("chain").eq(CHAIN_ID))


def get_blocks(event, context):
    blocks_table, _ = tables()
    return response(200, {"blocks": _all_blocks(blocks_table)})


def validate_chain(event, context):
    blocks_table, _ = tables()
    blocks = _all_blocks(blocks_table)
    errors = chain.validate(blocks)
    return response(200, {"valid": not errors, "blocks": len(blocks), "errors": errors})
