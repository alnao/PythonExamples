"""Logica della blockchain, senza AWS: hash dei blocchi, proof of work, verifica della catena.

Un blocco contiene le transazioni, l'hash del blocco precedente e un nonce. Come nelle blockchain vere
l'hash non e' calcolato su tutto il blocco ma su un'intestazione:
    index | timestamp | tx_root | previous_hash | difficulty | nonce
dove tx_root e' lo SHA-256 delle transazioni (JSON canonico). Il mining cerca il nonce che fa iniziare
l'hash con `difficulty` zeri esadecimali: cambiare una transazione cambia tx_root e quindi l'hash.
"""

import hashlib
import json
from decimal import Decimal

GENESIS_PREVIOUS_HASH = "0" * 64


def _plain(value):
    """Valori pronti per JSON. DynamoDB restituisce i numeri come Decimal: gli interi tornano int (come
    al momento del mining), gli altri diventano stringhe, cosi' l'hash non dipende dagli arrotondamenti dei float."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else str(value.normalize())
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def tx_for_block(tx: dict) -> dict:
    """Campi di una transazione che entrano nel blocco (e quindi nell'hash)."""
    return {k: tx[k] for k in ("id", "sender", "recipient", "amount", "timestamp")}


def transactions_root(transactions: list) -> str:
    """SHA-256 dell'elenco delle transazioni, con le chiavi in ordine."""
    text = json.dumps(_plain(transactions), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def _header(block: dict) -> str:
    return f"{int(block['index'])}|{int(block['timestamp'])}|{block['tx_root']}|{block['previous_hash']}|{int(block['difficulty'])}|"


def block_hash(block: dict) -> str:
    return hashlib.sha256((_header(block) + str(int(block["nonce"]))).encode()).hexdigest()


def mine(index: int, transactions: list, previous_hash: str, timestamp: int, difficulty: int) -> dict:
    """Proof of work: prova i nonce da 0 finche' l'hash inizia con `difficulty` zeri."""
    txs = [tx_for_block(tx) for tx in transactions]
    block = {"index": index, "timestamp": timestamp, "transactions": txs, "tx_root": transactions_root(txs),
             "previous_hash": previous_hash, "difficulty": difficulty}
    prefix, target, nonce = _header(block).encode(), "0" * difficulty, 0
    while True:
        h = hashlib.sha256(prefix + str(nonce).encode()).hexdigest()
        if h.startswith(target):
            return {**block, "nonce": nonce, "hash": h}
        nonce += 1


def validate(blocks: list) -> list:
    """Controlla la catena (blocchi in ordine di indice): ritorna l'elenco degli errori, vuoto se e' valida."""
    errors = []
    previous = GENESIS_PREVIOUS_HASH
    for expected_index, block in enumerate(blocks):
        index = int(block["index"])
        if index != expected_index:
            errors.append(f"blocco {index}: atteso l'indice {expected_index}")
        if block["previous_hash"] != previous:
            errors.append(f"blocco {index}: previous_hash non coincide con l'hash del blocco precedente")
        if transactions_root(block["transactions"]) != block["tx_root"]:
            errors.append(f"blocco {index}: le transazioni sono state modificate (tx_root diverso)")
        if block_hash(block) != block["hash"]:
            errors.append(f"blocco {index}: l'hash non corrisponde all'intestazione")
        if not block["hash"].startswith("0" * int(block["difficulty"])):
            errors.append(f"blocco {index}: l'hash non rispetta la difficolta' {block['difficulty']}")
        previous = block["hash"]
    return errors


def balances(transactions: list) -> dict:
    """Saldo di ogni indirizzo: somma delle transazioni ricevute meno quelle inviate."""
    result = {}
    for tx in transactions:
        amount = Decimal(str(tx["amount"]))
        result[tx["sender"]] = result.get(tx["sender"], Decimal(0)) - amount
        result[tx["recipient"]] = result.get(tx["recipient"], Decimal(0)) + amount
    return result
