"""Test delle Lambda e di upload_folder.py con S3, S3 Vectors e Bedrock finti (nessuna chiamata AWS)."""

import hashlib
import io
import json
import os
import sys

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.update(FILES_BUCKET="files", INDEX_ARN="arn:index")
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "lambda"))
sys.path.insert(0, ROOT)

import api  # noqa: E402
import ingest  # noqa: E402
import upload_folder  # noqa: E402
import wiki  # noqa: E402


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.store[Key] = Body if isinstance(Body, bytes) else Body.encode()

    def get_object(self, Bucket, Key):
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        data = self.store[Key]
        return {"Body": io.BytesIO(data), "ContentLength": len(data), "ETag": f'"{hashlib.md5(data).hexdigest()}"'}

    def delete_object(self, Bucket, Key):
        self.store.pop(Key, None)

    def copy_object(self, Bucket, Key, CopySource, **kw):
        self.copied = getattr(self, "copied", []) + [Key]

    def generate_presigned_post(self, Bucket, Key, Conditions, ExpiresIn):
        return {"url": f"https://{Bucket}.s3.eu-central-1.amazonaws.com/", "fields": {"key": Key}}

    def get_paginator(self, name):
        store = self.store

        class Paginator:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k, "ETag": f'"{hashlib.md5(store[k]).hexdigest()}"'}
                                    for k in sorted(store) if k.startswith(Prefix)]}
        return Paginator()


def matches(metadata, condition):
    """Valutazione dei filtri di S3 Vectors usati dalla wiki: $startsWith, $in, $eq e $and."""
    if "$and" in condition:
        return all(matches(metadata, c) for c in condition["$and"])
    (key, rule), = condition.items()
    value = metadata.get(key)
    if "$startsWith" in rule:
        return isinstance(value, str) and value.startswith(rule["$startsWith"])
    if "$in" in rule:
        return value in rule["$in"]
    return value == rule.get("$eq", rule)


class FakeVectors:
    def __init__(self):
        self.items = {}

    def put_vectors(self, indexArn, vectors):
        assert len(vectors) <= 500
        for v in vectors:
            assert len(json.dumps({k: v["metadata"][k] for k in v["metadata"] if k != "text"})) < 2048
            self.items[v["key"]] = v

    def delete_vectors(self, indexArn, keys):
        for k in keys:
            self.items.pop(k, None)

    def get_vectors(self, indexArn, keys, returnMetadata):
        assert len(keys) <= 100
        return {"vectors": [{"key": k, "metadata": self.items[k]["metadata"]} for k in keys if k in self.items]}

    def query_vectors(self, indexArn, topK, queryVector, returnMetadata, returnDistance, filter=None):
        self.last_filter = filter
        q = queryVector["float32"]
        candidates = [v for v in self.items.values() if not filter or matches(v["metadata"], filter)]
        scored = sorted(candidates, key=lambda v: -sum(a * b for a, b in zip(q, v["data"]["float32"])))
        return {"vectors": [{"key": v["key"], "metadata": v["metadata"], "distance": 0.2} for v in scored[:topK]]}


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FakeBedrock:
    def invoke_model(self, modelId, body, **kw):
        assert modelId == "amazon.titan-embed-text-v2:0"
        vec = [0.0] * 1024
        for word in json.loads(body)["inputText"].lower().replace("/", " ").split():
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % 1024] += 1.0
        return {"body": FakeBody(json.dumps({"embedding": vec}).encode())}


@pytest.fixture
def fakes(monkeypatch):
    s3, vectors = FakeS3(), FakeVectors()
    monkeypatch.setattr(wiki, "s3", s3)
    monkeypatch.setattr(wiki, "vectors", vectors)
    monkeypatch.setattr(wiki, "bedrock", FakeBedrock())
    monkeypatch.setattr(api, "_api_key", {"value": "segreta"})
    return s3, vectors


def call(method, path, body=None, params=None, key="segreta"):
    event = {"requestContext": {"http": {"method": method}}, "rawPath": path, "queryStringParameters": params,
             "headers": {"X-Api-Key": key} if key else {}, "body": json.dumps(body) if body is not None else None}
    result = api.handler(event, None)
    return result["statusCode"], json.loads(result["body"])


def s3_event(key, name="ObjectCreated:Put"):
    return {"Records": [{"eventName": name, "s3": {"object": {"key": key.replace(" ", "+")}}}]}


def add_file(s3, path, text):
    s3.store[f"files/{path}"] = text.encode()
    ingest.handler(s3_event(f"files/{path}"), None)


def test_split_lines_keeps_line_numbers():
    text = "\n".join(f"riga {i} " + "x" * 60 for i in range(1, 101))
    chunks = wiki.split_lines(text)
    assert chunks[0]["line_start"] == 1 and chunks[-1]["line_end"] == 100
    assert all(len(c["text"]) <= wiki.CHUNK_CHARS for c in chunks)
    # le parti si sovrappongono di OVERLAP_LINES righe
    assert chunks[1]["line_start"] == chunks[0]["line_end"] - wiki.OVERLAP_LINES + 1


def test_index_search_with_filters_and_delete(fakes):
    s3, vectors = fakes
    add_file(s3, "AWS/CDK/cdk15sqs/lambda/consumer.py", "def handler(event, context):\n    # legge i messaggi dalla coda sqs\n    pass")
    add_file(s3, "AWS/Lambda/py-example6-sqs-get/README.md", "# Lambda che legge da una coda sqs\nesempio serverless")
    add_file(s3, "Docker/09AwsDynamo/README.md", "# DynamoDB con docker compose\ntabella persone")
    assert call("GET", "/api/files/status", params={"path": "Docker/09AwsDynamo/README.md"})[1]["state"] == "ready"

    # senza filtri: i due file su sqs prima di quello su DynamoDB
    code, body = call("POST", "/api/search", {"question": "coda sqs", "k": 10})
    assert code == 200 and body["filter"] is None
    assert {r["path"] for r in body["results"][:2]} == {"AWS/CDK/cdk15sqs/lambda/consumer.py", "AWS/Lambda/py-example6-sqs-get/README.md"}
    assert body["results"][0]["snippets"][0]["line_start"] == 1

    # solo nella cartella AWS/CDK e solo file Python
    code, body = call("POST", "/api/search", {"question": "coda sqs", "folder": "AWS/CDK/", "extensions": [".py"]})
    assert vectors.last_filter == {"$and": [{"path": {"$startsWith": "AWS/CDK/"}}, {"extension": {"$in": [".py"]}}]}
    assert [r["path"] for r in body["results"]] == ["AWS/CDK/cdk15sqs/lambda/consumer.py"]

    # parti di un file e cancellazione (l'evento ObjectRemoved toglie vettori e stato)
    parts = call("GET", "/api/files/parts", params={"path": "Docker/09AwsDynamo/README.md"})[1]["parts"]
    assert parts[0]["line_start"] == 1 and "DynamoDB" in parts[0]["text"]
    assert call("DELETE", "/api/files", params={"path": "Docker/09AwsDynamo/README.md"})[0] == 200
    ingest.handler(s3_event("files/Docker/09AwsDynamo/README.md", "ObjectRemoved:Delete"), None)
    assert call("GET", "/api/files/status", params={"path": "Docker/09AwsDynamo/README.md"})[0] == 404
    assert all(v["metadata"]["path"] != "Docker/09AwsDynamo/README.md" for v in vectors.items.values())
    assert [f["path"] for f in call("GET", "/api/files")[1]["files"]] == [
        "AWS/CDK/cdk15sqs/lambda/consumer.py", "AWS/Lambda/py-example6-sqs-get/README.md"]


def test_errors_and_validation(fakes):
    s3, vectors = fakes
    assert call("GET", "/api/health", key=None) == (200, {"ok": True})
    assert call("GET", "/api/info", key=None)[1]["max_k"] == 100
    assert call("GET", "/api/files", key="no")[0] == 401
    assert call("POST", "/api/search", {"question": "x", "k": 101})[0] == 422
    assert call("POST", "/api/uploads", {"path": "../segreti.md"})[0] == 422
    assert call("POST", "/api/uploads", {"path": "foto.png"})[0] == 415
    code, body = call("POST", "/api/uploads", {"path": "/docs/guida.md"})
    assert code == 200 and body["upload"]["fields"]["key"] == "files/docs/guida.md"
    # file binario: stato di errore, nessun vettore
    s3.store["files/dati.json"] = b"\x00\x01binario"
    ingest.handler(s3_event("files/dati.json"), None)
    status = call("GET", "/api/files/status", params={"path": "dati.json"})[1]
    assert status["state"] == "error" and "binario" in status["error"] and not vectors.items


def test_upload_folder_selection_and_plan(tmp_path):
    (tmp_path / "AWS").mkdir()
    (tmp_path / "AWS" / "README.md").write_text("# AWS")
    (tmp_path / "AWS" / "app.py").write_text("print('ciao')")
    (tmp_path / "AWS" / "foto.png").write_bytes(b"\x89PNG")
    (tmp_path / "appunti.txt").write_text("chiave AKIAABCDEFGHIJKLMNOP da non pubblicare")
    (tmp_path / "note.md").write_text("appunti\nwJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n")
    (tmp_path / "locale.py").write_text('aws_secret_access_key="local"  # DynamoDB Local')
    (tmp_path / ".env").write_text("SEGRETO=1")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("x")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")

    local, skipped = upload_folder.local_files(str(tmp_path), "repo", excludes=["*/app.py"])
    assert sorted(local) == ["repo/AWS/README.md", "repo/locale.py"]
    assert dict(skipped) == {"repo/AWS/app.py": "escluso con --exclude", "repo/appunti.txt": "sembra contenere credenziali",
                             "repo/note.md": "sembra contenere credenziali"}
    del local["repo/locale.py"]

    remote = {"repo/AWS/README.md": "diverso", "repo/vecchio.md": "abc"}
    assert upload_folder.plan(local, remote, delete=False) == (["repo/AWS/README.md"], [], 0)
    remote["repo/AWS/README.md"] = local["repo/AWS/README.md"][1]
    assert upload_folder.plan(local, remote, delete=True) == ([], ["repo/vecchio.md"], 1)
