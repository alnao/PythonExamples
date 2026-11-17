"""Test delle Lambda del cdk12 con S3, Data API e DynamoDB finti (nessuna chiamata AWS)."""

import io
import json
import os
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.update(INPUT_FOLDER="INPUT", DEZIPPED_FOLDER="DEZIPPED", CSV_FOLDER="CSV", SFTP_FOLDER="TOSENDSFTP",
                  BUCKET_NAME="bucket", LOG_TABLE="log", SCAN_TABLE="scan", DB_CLUSTER_ARN="arn:cluster",
                  DB_SECRET_ARN="arn:secret", DB_NAME="es12db", DB_TABLE="es12table")
sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import api  # noqa: E402
import common  # noqa: E402
import database  # noqa: E402
import files  # noqa: E402
import scan  # noqa: E402

NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)


def error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "op")


class FakeS3:
    def __init__(self):
        self.objects = {}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[Key] = Body

    def get_paginator(self, name):
        fake = self

        class Paginator:
            def paginate(self, Bucket, Prefix=""):
                yield {"Contents": [{"Key": k, "Size": len(v), "LastModified": NOW}
                                    for k, v in sorted(fake.objects.items()) if k.startswith(Prefix)]}
        return Paginator()


class FakeRdsData:
    """Database MySQL minimo: una tabella con colonne e righe, ed eventualmente in pausa per N chiamate."""

    def __init__(self, paused_calls=0):
        self.columns, self.rows, self.paused_calls, self.statements = [], [], paused_calls, []

    def _resume(self):
        if self.paused_calls:
            self.paused_calls -= 1
            raise error("DatabaseResumingException")

    def execute_statement(self, sql, **kwargs):
        self._resume()
        self.statements.append(sql)
        if sql.startswith("SELECT COLUMN_NAME"):
            return {"records": [[{"stringValue": c}] for c in self.columns]}
        if sql.startswith("CREATE TABLE"):
            self.columns = [part.split("`")[1] for part in sql.split("(", 1)[1].split(", ")]
            return {}
        if sql.startswith("SELECT *"):
            if not self.columns:
                raise error("BadRequestException: Table 'es12db.es12table' doesn't exist")
            return {"formattedRecords": json.dumps(self.rows)}
        raise AssertionError(sql)

    def batch_execute_statement(self, sql, parameterSets, **kwargs):
        self._resume()
        names = [c.strip("` ") for c in sql.split("(", 1)[1].split(")")[0].split(",")]
        for params in parameterSets:
            self.rows.append({n: p["value"]["stringValue"] for n, p in zip(names, params)})
        return {}


class FakeDynamoClient:
    def __init__(self):
        self.tables = {"log": {}, "scan": {}}

    def put_item(self, TableName, Item, ConditionExpression=None):
        key = Item["id"]["S"]
        if ConditionExpression and key in self.tables[TableName]:
            raise error("ConditionalCheckFailedException")
        self.tables[TableName][key] = Item

    def update_item(self, TableName, Key, UpdateExpression, ExpressionAttributeValues):
        item = self.tables[TableName][Key["id"]["S"]]
        item["nuovo"], item["dataOraAggiornamentoRiga"] = ExpressionAttributeValues[":n"], ExpressionAttributeValues[":d"]


@pytest.fixture
def aws(monkeypatch):
    fakes = {"s3": FakeS3(), "rds-data": FakeRdsData(), "dynamodb": FakeDynamoClient()}
    monkeypatch.setattr(common, "_clients", fakes)
    monkeypatch.setattr(database.time, "sleep", lambda s: None)
    return fakes


def created(key):
    return {"source": "aws.s3", "detail-type": "Object Created",
            "detail": {"bucket": {"name": "bucket"}, "object": {"key": key}}}


def excel_bytes(rows):
    workbook = openpyxl.Workbook()
    for row in rows:
        workbook.active.append(row)
    data = io.BytesIO()
    workbook.save(data)
    return data.getvalue()


# ---- file ----

def test_decompress_zip_keeps_files_inside_folder(aws):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr("dati/persone.xlsx", b"excel")
        z.writestr("../../fuori.txt", b"tentativo di uscire dalla cartella")
        z.writestr("vuota/", b"")
    aws["s3"].objects["INPUT/test.zip"] = data.getvalue()
    result = files.decompress(created("INPUT/test.zip"), None)
    assert sorted(result["file"]) == ["DEZIPPED/dati/persone.xlsx", "DEZIPPED/fuori.txt"]


def test_decompress_tar_gz(aws):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as tar:
        info = tarfile.TarInfo("a.csv")
        info.size = 3
        tar.addfile(info, io.BytesIO(b"x,y"))
    aws["s3"].objects["INPUT/t.tgz"] = data.getvalue()
    assert files.decompress(created("INPUT/t.tgz"), None)["file"] == ["DEZIPPED/a.csv"]
    assert aws["s3"].objects["DEZIPPED/a.csv"] == b"x,y"


def test_s3_notification_event_key_is_decoded():
    event = {"Records": [{"s3": {"bucket": {"name": "b"}, "object": {"key": "INPUT/nome+con+spazi.zip"}}}]}
    assert common.s3_object(event) == ("b", "INPUT/nome con spazi.zip")


def test_convert_excel_to_csv(aws):
    aws["s3"].objects["DEZIPPED/dati/persone.xlsx"] = excel_bytes([["Nome", "Eta"], ["Alberto", 24], [None, None], ["Andrea", None]])
    assert files.convert_to_csv(created("DEZIPPED/dati/persone.xlsx"), None)["csv"] == "CSV/persone.csv"
    assert aws["s3"].objects["CSV/persone.csv"].decode() == "Nome,Eta\nAlberto,24\nAndrea,\n"


# ---- database ----

def test_parse_csv_safe_column_names():
    columns, rows = database.parse_csv("\ufeffNome;Età;Nome;`DROP TABLE x`;\nAlberto;24;bis;z;w\n\n")
    assert columns == ["Nome", "Et", "Nome_3", "DROP_TABLE_x", "colonna5"]
    assert rows == [["Alberto", "24", "bis", "z", "w"]]


def test_process_csv_creates_table_and_ignores_new_columns(aws):
    aws["s3"].objects["CSV/primo.csv"] = b"Nome,Cognome\nAlberto,Nao\nAndrea,Nao\n"
    assert database.process_csv(created("CSV/primo.csv"), None)["righe"] == 2
    assert aws["rds-data"].columns == ["Nome", "Cognome"]
    aws["s3"].objects["CSV/secondo.csv"] = b"Cognome,Citta\nGaltarossa,Verona\n"
    result = database.process_csv(created("CSV/secondo.csv"), None)
    assert result["colonne_ignorate"] == ["Citta"]
    assert aws["rds-data"].rows[-1] == {"Cognome": "Galtarossa"}
    logs = list(aws["dynamodb"].tables["log"].values())
    assert [log["esito_caricamento"]["S"] for log in logs] == ["Successo", "Successo"]
    assert logs[1]["colonne_ignorate"] == {"L": [{"S": "Citta"}]}


def test_process_csv_waits_for_paused_database(aws):
    aws["rds-data"].paused_calls = 3
    aws["s3"].objects["CSV/a.csv"] = b"A\n1\n"
    assert database.process_csv(created("CSV/a.csv"), None)["righe"] == 1


def test_process_csv_error_is_logged_and_raised(aws):
    aws["s3"].objects["CSV/vuoto.csv"] = b"\n"
    with pytest.raises(ValueError):
        database.process_csv(created("CSV/vuoto.csv"), None)
    log = next(iter(aws["dynamodb"].tables["log"].values()))
    assert log["esito_caricamento"]["S"] == "Errore: CSV vuoto"


def test_read_rds(aws):
    assert json.loads(database.read_rds({}, None)["body"]) == []  # tabella non ancora creata
    aws["rds-data"].columns, aws["rds-data"].rows = ["Nome"], [{"Nome": "Alberto"}]
    assert json.loads(database.read_rds({}, None)["body"]) == [{"Nome": "Alberto"}]
    aws["rds-data"].paused_calls = 10
    assert database.read_rds({}, None)["statusCode"] == 503


# ---- API ----

def test_upload_zip_validation():
    assert api.upload_zip({"queryStringParameters": None}, None)["statusCode"] == 400
    assert api.upload_zip({"queryStringParameters": {"file_name": "dati.xlsx"}}, None)["statusCode"] == 400


def test_upload_zip_presigned_url():
    body = json.loads(api.upload_zip({"queryStringParameters": {"file_name": "../dati.zip"}}, None)["body"])
    assert body["key"] == "INPUT/dati.zip" and "X-Amz-Signature" in body["upload_url"]


def test_download_only_excel_in_dezipped():
    for key in ("CSV/a.csv", "DEZIPPED/../CSV/a.xlsx", "DEZIPPED/a.csv", None):
        assert api.download_excel_file({"queryStringParameters": {"file_key": key}}, None)["statusCode"] == 400
    ok = api.download_excel_file({"queryStringParameters": {"file_key": "DEZIPPED/dati/a.xlsx"}}, None)
    assert ok["statusCode"] == 200 and "download_url" in json.loads(ok["body"])


def test_list_excel_files(aws):
    aws["s3"].objects.update({"DEZIPPED/a.xlsx": b"1", "DEZIPPED/b.txt": b"2", "CSV/a.csv": b"3"})
    body = json.loads(api.list_excel_files({}, None)["body"])
    assert [f["key"] for f in body] == ["DEZIPPED/a.xlsx"] and body[0]["last_modified"].startswith("2026-11-17")


def test_find_file_requires_name():
    assert api.find_file({"queryStringParameters": {}}, None)["statusCode"] == 400


# ---- scansione ----

def test_scan_marks_new_and_known_files(aws):
    aws["s3"].objects.update({"INPUT/a.zip": b"12", "CSV/b.csv": b"1"})
    assert scan.scan_bucket({}, None) == {"nuovi": 2, "gia_presenti": 0}
    aws["s3"].objects["CSV/c.csv"] = b"1"
    assert scan.scan_bucket({}, None) == {"nuovi": 1, "gia_presenti": 2}
    items = {i["nomeFile"]["S"]: i for i in aws["dynamodb"].tables["scan"].values()}
    assert items["a.zip"]["nuovo"] == {"S": "N"} and items["c.csv"]["nuovo"] == {"S": "S"}
    assert items["a.zip"]["path"] == {"S": "INPUT"} and items["a.zip"]["dimensione"] == {"N": "2"}
