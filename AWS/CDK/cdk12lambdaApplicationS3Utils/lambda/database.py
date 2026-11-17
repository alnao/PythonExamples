"""Lambda sul database Aurora MySQL, tramite la Data API di RDS (HTTPS: le Lambda non stanno nella VPC).

- process_csv: CSV caricato in CSV/ -> righe inserite nella tabella (creata alla prima volta con le colonne del CSV,
  VARCHAR(100)); le colonne del CSV che la tabella non ha vengono ignorate; una riga di log in DynamoDB
- read_rds: API GET /read-rds-data, al massimo 1000 righe della tabella

Il cluster Aurora Serverless v2 va in pausa dopo 5 minuti senza connessioni: alla prima richiesta la Data API
risponde DatabaseResumingException finche' il database non riparte (qualche secondo), quindi le chiamate riprovano.
"""

import csv
import io
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from common import client, response, s3_object

MAX_LENGTH = 100   # le colonne create sono VARCHAR(100)
BATCH_SIZE = 200   # righe per ogni chiamata BatchExecuteStatement
IDENTIFIER = re.compile(r"^[A-Za-z0-9_]{1,64}$")


class DatabaseResuming(Exception):
    pass


def _table() -> str:
    table = os.environ["DB_TABLE"]
    if not IDENTIFIER.match(table):
        raise ValueError(f"nome di tabella non valido: {table}")
    return table


def _call(method: str, attempts: int, **kwargs) -> dict:
    """Chiamata alla Data API con nuovi tentativi mentre il cluster riparte dalla pausa."""
    params = {"resourceArn": os.environ["DB_CLUSTER_ARN"], "secretArn": os.environ["DB_SECRET_ARN"],
              "database": os.environ["DB_NAME"], **kwargs}
    for attempt in range(attempts):
        try:
            return getattr(client("rds-data"), method)(**params)
        except ClientError as e:
            if e.response["Error"]["Code"] != "DatabaseResumingException":
                raise
            print(f"database in ripresa dalla pausa (tentativo {attempt + 1}/{attempts})")
            time.sleep(5)
    raise DatabaseResuming("il database si sta riavviando dalla pausa, riprovare tra qualche secondo")


def column_name(header: str, index: int) -> str:
    """Nome di colonna sicuro per SQL: lettere, numeri e _ (i nomi del CSV non finiscono mai nella query cosi' come sono)."""
    name = re.sub(r"[^0-9A-Za-z_]", "_", header.strip()).strip("_")[:64]
    return name or f"colonna{index + 1}"


def parse_csv(text: str) -> tuple:
    """Colonne (nomi sicuri, senza doppioni) e righe del CSV; separatore , oppure ; riconosciuto dalla prima riga."""
    text = text.lstrip("﻿")
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("CSV vuoto")
    columns, seen = [], set()
    for i, header in enumerate(rows[0]):
        name = column_name(header, i)
        while name.lower() in seen:
            name = f"{name}_{i + 1}"
        seen.add(name.lower())
        columns.append(name)
    return columns, rows[1:]


def existing_columns(attempts: int) -> list:
    result = _call("execute_statement", attempts,
        sql="SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
            "ORDER BY ORDINAL_POSITION",
        parameters=[{"name": "t", "value": {"stringValue": _table()}}])
    return [record[0]["stringValue"] for record in result.get("records", [])]


def _log(file_name: str, outcome: str, **extra):
    item = {"id": str(uuid.uuid4()), "nome_file": file_name, "esito_caricamento": outcome,
            "data_caricamento": datetime.now(timezone.utc).isoformat(), **extra}
    client("dynamodb").put_item(TableName=os.environ["LOG_TABLE"],
                                Item={k: ({"N": str(v)} if isinstance(v, int) else
                                          {"L": [{"S": x} for x in v]} if isinstance(v, list) else {"S": v})
                                      for k, v in item.items()})
    print(f"log: {json.dumps(item)}")


def process_csv(event, context):
    bucket, key = s3_object(event)
    file_name = os.path.basename(key)
    try:
        text = client("s3").get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        columns, rows = parse_csv(text)
        table = _table()
        existing = existing_columns(attempts=12)
        if not existing:
            definition = ", ".join(f"`{c}` VARCHAR({MAX_LENGTH})" for c in columns)
            _call("execute_statement", 12, sql=f"CREATE TABLE IF NOT EXISTS `{table}` ({definition})")
            existing = columns
        lower_existing = {c.lower() for c in existing}
        used = [i for i, c in enumerate(columns) if c.lower() in lower_existing]
        ignored = [c for c in columns if c.lower() not in lower_existing]
        if used:
            sql = (f"INSERT INTO `{table}` ({', '.join(f'`{columns[i]}`' for i in used)}) "
                   f"VALUES ({', '.join(f':p{n}' for n in range(len(used)))})")
            parameter_sets = [[{"name": f"p{n}", "value": {"stringValue": (row[i] if i < len(row) else "")[:MAX_LENGTH]}}
                               for n, i in enumerate(used)] for row in rows]
            for start in range(0, len(parameter_sets), BATCH_SIZE):
                _call("batch_execute_statement", 12, sql=sql, parameterSets=parameter_sets[start:start + BATCH_SIZE])
        _log(file_name, "Successo", righe=len(rows), colonne_ignorate=ignored)
        return {"file": key, "righe": len(rows), "colonne_ignorate": ignored}
    except Exception as e:
        _log(file_name, f"Errore: {e}")
        raise  # la Lambda termina con errore: lo conta la metrica Errors (allarme)


def read_rds(event, context):
    try:
        result = _call("execute_statement", 4, sql=f"SELECT * FROM `{_table()}` LIMIT 1000", formatRecordsAs="JSON")
        return response(200, json.loads(result.get("formattedRecords") or "[]"))
    except DatabaseResuming as e:
        return response(503, {"errore": str(e)})
    except ClientError as e:
        if "doesn't exist" in str(e):  # tabella non ancora creata: la crea il primo CSV elaborato
            return response(200, [])
        raise
