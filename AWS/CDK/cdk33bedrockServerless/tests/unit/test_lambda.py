"""Test delle Lambda con S3, S3 Vectors e Bedrock finti (nessuna chiamata AWS)."""

import hashlib
import io
import json
import os
import sys

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.update(DOCS_BUCKET="docs", INDEX_ARN="arn:index", CHUNK_SIZE="300", CHUNK_OVERLAP="60")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import api  # noqa: E402
import ingest  # noqa: E402
import rag  # noqa: E402


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.store[Key] = Body

    def get_object(self, Bucket, Key):
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[Key])}

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.store.pop(obj["Key"], None)

    def copy_object(self, Bucket, Key, CopySource, **kw):
        self.copied = getattr(self, "copied", []) + [Key]

    def generate_presigned_post(self, Bucket, Key, Conditions, ExpiresIn):
        return {"url": f"https://{Bucket}.s3.eu-central-1.amazonaws.com/", "fields": {"key": Key}}

    def get_paginator(self, name):
        store = self.store

        class Paginator:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k} for k in sorted(store) if k.startswith(Prefix)]}
        return Paginator()


class FakeVectors:
    def __init__(self):
        self.items = {}

    def put_vectors(self, indexArn, vectors):
        assert len(vectors) <= 500
        for v in vectors:
            self.items[v["key"]] = v

    def delete_vectors(self, indexArn, keys):
        for k in keys:
            self.items.pop(k, None)

    def get_vectors(self, indexArn, keys, returnMetadata):
        assert len(keys) <= 100
        return {"vectors": [{"key": k, "metadata": self.items[k]["metadata"]} for k in keys if k in self.items]}

    def query_vectors(self, indexArn, topK, queryVector, returnMetadata, returnDistance, nextToken=None):
        # come S3 Vectors: al massimo 100 risultati per pagina, nextToken per le successive
        self.query_calls = getattr(self, "query_calls", 0) + 1
        q = queryVector["float32"]
        scored = sorted(self.items.values(), key=lambda v: -sum(a * b for a, b in zip(q, v["data"]["float32"])))[:topK]
        start = int(nextToken or 0)
        page = scored[start:start + 100]
        response = {"vectors": [{"key": v["key"], "metadata": v["metadata"], "distance": 0.1} for v in page]}
        if start + 100 < len(scored):
            response["nextToken"] = str(start + 100)
        return response


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FakeBedrock:
    def __init__(self):
        self.converse_calls = []

    def invoke_model(self, modelId, body, **kw):
        vec = [0.0] * 1024
        for word in json.loads(body)["inputText"].lower().split():
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % 1024] += 1.0
        return {"body": FakeBody(json.dumps({"embedding": vec}).encode())}

    def converse(self, modelId, messages, **kw):
        self.converse_calls.append({"modelId": modelId, "kw": kw})
        return {"output": {"message": {"content": [{"text": "Risposta [1]"}]}}, "stopReason": "end_turn"}


@pytest.fixture
def fakes(monkeypatch):
    s3, vectors, bedrock = FakeS3(), FakeVectors(), FakeBedrock()
    monkeypatch.setattr(rag, "s3", s3)
    monkeypatch.setattr(rag, "vectors", vectors)
    monkeypatch.setattr(rag, "bedrock", bedrock)
    monkeypatch.setattr(api, "_api_key", {"value": "segreta"})
    return s3, vectors, bedrock


def call(method, path, body=None, key="segreta"):
    event = {"requestContext": {"http": {"method": method}}, "rawPath": path,
             "headers": {"X-Api-Key": key} if key else {}, "body": json.dumps(body) if body is not None else None}
    result = api.handler(event, None)
    return result["statusCode"], json.loads(result["body"])


def s3_event(key):
    return {"Records": [{"s3": {"object": {"key": key.replace(" ", "+")}}}]}


def test_split_text_overlap():
    text = "\n\n".join(f"Paragrafo {i}. " + "parola " * 40 for i in range(6))
    chunks = rag.split_text(text, size=300, overlap=60)
    assert len(chunks) > 1
    assert all(len(c) <= 300 + 60 + 2 for c in chunks)
    assert chunks[1].startswith("parola")


def test_auth_and_routes(fakes):
    assert call("GET", "/api/health", key=None) == (200, {"ok": True})
    assert call("GET", "/api/documents", key=None)[0] == 401
    assert call("GET", "/api/documents", key="sbagliata")[0] == 401
    assert call("GET", "/api/nulla")[0] == 404
    assert call("POST", "/api/query", {"question": ""})[0] == 422


def test_upload_ingest_query_forget(fakes):
    s3, vectors, bedrock = fakes
    status, body = call("POST", "/api/uploads", {"filename": "contratto.txt", "doc_id": "Contratto 2026"})
    assert status == 200 and body["doc_id"] == "Contratto-2026"
    assert body["upload"]["fields"]["key"] == "uploads/Contratto-2026/contratto.txt"
    assert call("GET", "/api/documents/Contratto-2026/status")[1]["state"] == "uploading"
    assert call("POST", "/api/uploads", {"filename": "virus.exe"})[0] == 415

    # il browser carica il file, S3 avvisa la Lambda di indicizzazione
    text = "\n\n".join(["La durata del contratto è di dodici mesi.", "Il pagamento è a trenta giorni."] * 10)
    s3.store[body["key"]] = text.encode()
    ingest.handler(s3_event(body["key"]), None)
    status = call("GET", "/api/documents/Contratto-2026/status")[1]
    assert status["state"] == "ready" and status["chunks"] == len(vectors.items) > 1

    code, answer = call("POST", "/api/query", {"question": "durata del contratto", "k": 2})
    assert code == 200 and answer["answer"] == "Risposta [1]" and len(answer["sources"]) == 2
    assert answer["sources"][0]["filename"] == "contratto.txt" and "excerpt" in answer["sources"][0]
    assert bedrock.converse_calls[-1]["kw"]["inferenceConfig"]["temperature"] == 0.2

    chunks = call("GET", "/api/documents/Contratto-2026")[1]["chunks"]
    assert [c["chunk"] for c in chunks] == list(range(status["chunks"]))

    # nuova versione piu' corta con altro nome: vettori in piu' e vecchio file cancellati
    body = call("POST", "/api/uploads", {"filename": "contratto-v2.txt", "doc_id": "Contratto-2026"})[1]
    s3.store[body["key"]] = b"Versione breve."
    ingest.handler(s3_event(body["key"]), None)
    assert call("GET", "/api/documents/Contratto-2026/status")[1]["chunks"] == 1
    assert list(vectors.items) == ["Contratto-2026#00000"]
    assert "uploads/Contratto-2026/contratto.txt" not in s3.store

    # reindex rimette in coda i file
    assert call("POST", "/api/reindex")[1]["queued"] == ["uploads/Contratto-2026/contratto-v2.txt"]

    # forget
    code, result = call("DELETE", "/api/documents/Contratto-2026")
    assert code == 200 and result["deleted_chunks"] == 1
    assert not vectors.items and not [k for k in s3.store if "Contratto-2026" in k]
    assert call("DELETE", "/api/documents/Contratto-2026")[0] == 404


def test_ingest_error_and_image(fakes):
    s3, vectors, bedrock = fakes
    s3.store["uploads/vuoto/vuoto.txt"] = b"   "
    ingest.handler(s3_event("uploads/vuoto/vuoto.txt"), None)
    status = call("GET", "/api/documents/vuoto/status")[1]
    assert status["state"] == "error" and "nessun testo" in status["error"]

    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, format="BMP")
    s3.store["uploads/foto/foto.bmp"] = buffer.getvalue()
    ingest.handler(s3_event("uploads/foto/foto.bmp"), None)
    assert call("GET", "/api/documents/foto/status")[1]["state"] == "ready"
    image_call = bedrock.converse_calls[-1]
    assert image_call["modelId"] == "eu.amazon.nova-lite-v1:0"
    assert "temperature" not in image_call["kw"]["inferenceConfig"]
    assert [d["doc_id"] for d in call("GET", "/api/documents")[1]["documents"]] == ["foto", "vuoto"]


def test_images_disabled(fakes, monkeypatch):
    s3, vectors, bedrock = fakes
    monkeypatch.setattr(rag, "IMAGE_MODEL", "")
    s3.store["uploads/foto/foto.png"] = b"non importa"
    ingest.handler(s3_event("uploads/foto/foto.png"), None)
    status = call("GET", "/api/documents/foto/status")[1]
    assert status["state"] == "error" and "IMAGE_MODEL" in status["error"]
    assert not bedrock.converse_calls


def test_aws_error_is_readable(fakes, monkeypatch):
    s3, vectors, bedrock = fakes

    def end_of_life(**kw):
        raise ClientError({"Error": {"Code": "ResourceNotFoundException",
                                     "Message": "This model version has reached the end of its life."}}, "Converse")
    s3.store["uploads/a/a.txt"] = b"testo di prova"
    ingest.handler(s3_event("uploads/a/a.txt"), None)
    monkeypatch.setattr(bedrock, "converse", end_of_life)
    code, body = call("POST", "/api/query", {"question": "prova", "k": 1})
    assert code == 502 and "end of its life" in body["detail"]
    assert rag.CHAT_MODEL == "eu.amazon.nova-lite-v1:0"


def test_time_running_out(fakes):
    """Con meno di un minuto rimasto la Lambda si ferma con uno stato di errore chiaro."""
    s3, vectors, bedrock = fakes

    class Context:
        def get_remaining_time_in_millis(self):
            return 30_000
    s3.store["uploads/grande/grande.txt"] = ("parola " * 50000).encode()
    ingest.handler(s3_event("uploads/grande/grande.txt"), Context())
    status = call("GET", "/api/documents/grande/status")[1]
    assert status["state"] == "error" and "tempo esaurito" in status["error"]
    assert not vectors.items


def test_upload_limit(fakes):
    assert api.MAX_UPLOAD_MB >= 1
    body = call("GET", "/api/supported-formats", key=None)[1]
    assert body["max_upload_mb"] == api.MAX_UPLOAD_MB


def test_many_sources_and_context_budget(fakes, monkeypatch):
    s3, vectors, bedrock = fakes
    text = "\n\n".join(f"Paragrafo {i}: " + "contenuto del documento " * 10 for i in range(250))
    s3.store["uploads/lungo/lungo.txt"] = text.encode()
    ingest.handler(s3_event("uploads/lungo/lungo.txt"), None)
    total = call("GET", "/api/documents/lungo/status")[1]["chunks"]
    assert total > 100

    # 1000 brani richiesti: tutti quelli che ci sono, letti a pagine da 100
    vectors.query_calls = 0
    code, body = call("POST", "/api/query", {"question": "contenuto", "k": 1000})
    assert code == 200 and body["found"] == total and body["used"] == total == len(body["sources"])
    assert vectors.query_calls == (total + 99) // 100

    # budget del contesto piccolo: trovati tutti, usati solo quelli che ci stanno
    monkeypatch.setattr(rag, "CONTEXT_MAX_CHARS", 1500)
    code, body = call("POST", "/api/query", {"question": "contenuto", "k": 42})
    assert code == 200 and body["found"] == 42 and 1 <= body["used"] < 42 == body["found"]
    assert [x["n"] for x in body["sources"]] == list(range(1, body["used"] + 1))

    assert call("POST", "/api/query", {"question": "contenuto", "k": 1001})[0] == 422
    assert call("GET", "/api/supported-formats", key=None)[1]["max_k"] == 1000
