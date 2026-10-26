"""Test delle Lambda con S3, Bedrock e Knowledge Base finti (nessuna chiamata AWS)."""

import json
import os
import sys
from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError

os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.update(DOCS_BUCKET="docs", KNOWLEDGE_BASE_ID="KB123", DATA_SOURCE_ID="DS123")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda"))

import api  # noqa: E402
import kb  # noqa: E402
import sync  # noqa: E402

NOW = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


class FakeS3:
    def __init__(self):
        self.store = {}

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.store.pop(obj["Key"], None)

    def generate_presigned_post(self, Bucket, Key, Conditions, ExpiresIn):
        return {"url": f"https://{Bucket}.s3.eu-central-1.amazonaws.com/", "fields": {"key": Key}}

    def get_paginator(self, name):
        store = self.store

        class Paginator:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k, "Size": len(v), "LastModified": NOW}
                                    for k, v in sorted(store.items()) if k.startswith(Prefix)]}
        return Paginator()


class FakeAgent:
    """bedrock-agent: stato dei documenti e sincronizzazioni (una sola alla volta, come AWS)."""

    def __init__(self):
        self.statuses = {}
        self.running = False
        self.started = []

    def list_knowledge_base_documents(self, knowledgeBaseId, dataSourceId, maxResults, nextToken=None):
        assert (knowledgeBaseId, dataSourceId) == ("KB123", "DS123")
        return {"documentDetails": [{"identifier": {"dataSourceType": "S3", "s3": {"uri": uri}}, "status": status,
                                     "statusReason": "file illeggibile" if status == "FAILED" else "", "updatedAt": NOW}
                                    for uri, status in self.statuses.items()]}

    def start_ingestion_job(self, knowledgeBaseId, dataSourceId, description):
        assert len(description) <= 200
        if self.running:
            raise ClientError({"Error": {"Code": "ConflictException", "Message": "job in corso"}}, "StartIngestionJob")
        self.running = True
        self.started.append(description)
        return {"ingestionJob": {"ingestionJobId": f"JOB{len(self.started)}", "status": "STARTING",
                                 "description": description, "startedAt": NOW, "updatedAt": NOW}}

    def list_ingestion_jobs(self, knowledgeBaseId, dataSourceId, sortBy, maxResults):
        return {"ingestionJobSummaries": [{"ingestionJobId": "JOB1", "status": "COMPLETE", "startedAt": NOW, "updatedAt": NOW,
                                           "statistics": {"numberOfDocumentsScanned": 3, "numberOfNewDocumentsIndexed": 1,
                                                          "numberOfModifiedDocumentsIndexed": 1, "numberOfDocumentsDeleted": 1,
                                                          "numberOfDocumentsFailed": 0}}]}


class FakeAgentRuntime:
    def __init__(self):
        self.results = []

    def retrieve(self, knowledgeBaseId, retrievalQuery, retrievalConfiguration):
        k = retrievalConfiguration["vectorSearchConfiguration"]["numberOfResults"]
        assert knowledgeBaseId == "KB123" and 1 <= k <= 100
        return {"retrievalResults": self.results[:k]}


class FakeBedrock:
    def __init__(self):
        self.converse_calls = []

    def converse(self, modelId, messages, **kw):
        self.converse_calls.append({"modelId": modelId, "prompt": messages[0]["content"][0]["text"], "kw": kw})
        return {"output": {"message": {"content": [{"text": "Dura due anni [1]"}]}}, "stopReason": "end_turn"}


@pytest.fixture
def fakes(monkeypatch):
    s3, agent, runtime, bedrock = FakeS3(), FakeAgent(), FakeAgentRuntime(), FakeBedrock()
    monkeypatch.setattr(kb, "s3", s3)
    monkeypatch.setattr(kb, "agent", agent)
    monkeypatch.setattr(kb, "agent_runtime", runtime)
    monkeypatch.setattr(kb, "bedrock", bedrock)
    monkeypatch.setattr(api, "_api_key", {"value": "segreta"})
    return s3, agent, runtime, bedrock


def call(method, path, body=None, key="segreta"):
    event = {"requestContext": {"http": {"method": method}}, "rawPath": path,
             "headers": {"X-Api-Key": key} if key else {}, "body": json.dumps(body) if body is not None else None}
    result = api.handler(event, None)
    return result["statusCode"], json.loads(result["body"])


def sqs_event(*bodies):
    return {"Records": [{"body": json.dumps(b)} for b in bodies]}


def s3_notification(*keys):
    return {"Records": [{"eventName": "ObjectCreated:Post", "s3": {"object": {"key": k.replace(" ", "+")}}} for k in keys]}


def retrieval(key, text, score=0.8, page=None):
    metadata = {"x-amz-bedrock-kb-source-uri": f"s3://docs/{key}"}
    if page:
        metadata["x-amz-bedrock-kb-document-page-number"] = float(page)
    return {"content": {"text": text, "type": "TEXT"}, "score": score, "metadata": metadata,
            "location": {"type": "S3", "s3Location": {"uri": f"s3://docs/{key}"}}}


def test_auth_and_routes(fakes):
    assert call("GET", "/api/health", key=None) == (200, {"ok": True})
    assert call("GET", "/api/supported-formats", key=None)[1]["max_k"] == 100
    assert call("GET", "/api/documents", key=None)[0] == 401
    assert call("GET", "/api/documents", key="sbagliata")[0] == 401
    assert call("GET", "/api/nulla")[0] == 404
    assert call("POST", "/api/query", {"question": ""})[0] == 422
    assert call("POST", "/api/query", {"question": "x", "k": 101})[0] == 422
    assert call("POST", "/api/query", {"question": "x", "mode": "altro"})[0] == 422


def test_upload_replaces_previous_file(fakes):
    s3, *_ = fakes
    s3.store["uploads/contratto/vecchio.pdf"] = b"v1"
    s3.store["uploads/contratto-bis/altro.pdf"] = b"resta"
    code, body = call("POST", "/api/uploads", {"filename": "Contratto 2026.docx", "doc_id": "contratto"})
    assert code == 200 and body["key"] == "uploads/contratto/Contratto 2026.docx"
    assert body["upload"]["fields"]["key"] == body["key"]
    # il file precedente dello stesso documento viene cancellato, quello di un altro documento no
    assert sorted(s3.store) == ["uploads/contratto-bis/altro.pdf"]
    assert call("POST", "/api/uploads", {"filename": "foto.png"})[0] == 415
    assert call("POST", "/api/uploads", {"filename": "Relazione finale.pdf"})[1]["doc_id"] == "Relazione-finale"


def test_documents_with_knowledge_base_status(fakes):
    s3, agent, *_ = fakes
    s3.store.update({"uploads/a/a.pdf": b"1", "uploads/b/b.txt": b"22", "uploads/c/c.md": b"333", "uploads/rotto": b""})
    agent.statuses = {"s3://docs/uploads/a/a.pdf": "INDEXED", "s3://docs/uploads/b/b.txt": "FAILED"}
    code, body = call("GET", "/api/documents")
    docs = {d["doc_id"]: d for d in body["documents"]}
    assert code == 200 and sorted(docs) == ["a", "b", "c"]
    assert docs["a"]["status"] == "INDEXED" and docs["a"]["filename"] == "a.pdf" and docs["a"]["size"] == 1
    assert docs["b"]["status"] == "FAILED" and docs["b"]["reason"] == "file illeggibile"
    # caricato ma non ancora visto da una sincronizzazione
    assert docs["c"]["status"] == "NOT_SYNCED"
    assert call("GET", "/api/documents/c/status")[1]["status"] == "NOT_SYNCED"
    assert call("GET", "/api/documents/zzz/status")[0] == 404


def test_forget_deletes_files(fakes):
    s3, *_ = fakes
    s3.store.update({"uploads/a/a.pdf": b"1", "uploads/ab/ab.pdf": b"2"})
    assert call("DELETE", "/api/documents/a") == (200, {"status": "ok", "doc_id": "a", "deleted_files": 1})
    assert list(s3.store) == ["uploads/ab/ab.pdf"]
    assert call("DELETE", "/api/documents/a")[0] == 404


def test_query_answer_with_sources(fakes):
    _, _, runtime, bedrock = fakes
    runtime.results = [retrieval("uploads/contratto/c.pdf", "La durata e' di due anni.", 0.91234, page=3),
                       retrieval("uploads/note/n.txt", "Altro testo.", 0.5)]
    code, body = call("POST", "/api/query", {"question": "Quanto dura?", "k": 5})
    assert code == 200 and body["answer"] == "Dura due anni [1]" and body["found"] == 2
    assert body["sources"][0] == {"n": 1, "doc_id": "contratto", "filename": "c.pdf", "page": 3, "score": 0.912,
                                  "excerpt": "La durata e' di due anni."}
    assert body["sources"][1]["page"] is None
    prompt = bedrock.converse_calls[0]["prompt"]
    assert "[1] (file c.pdf, pagina 3)\nLa durata" in prompt and "[2] (file n.txt)" in prompt
    assert bedrock.converse_calls[0]["kw"]["system"][0]["text"] == kb.SYSTEM_PROMPT


def test_query_search_only_and_empty(fakes):
    _, _, runtime, bedrock = fakes
    assert call("POST", "/api/query", {"question": "x"})[1]["found"] == 0
    runtime.results = [retrieval("uploads/a/a.md", "testo")]
    code, body = call("POST", "/api/query", {"question": "x", "mode": "search"})
    assert code == 200 and body["answer"] is None and body["sources"][0]["filename"] == "a.md"
    assert not bedrock.converse_calls


def test_sync_from_admin(fakes):
    _, agent, *_ = fakes
    code, body = call("POST", "/api/sync")
    assert code == 200 and body["id"] == "JOB1" and body["status"] == "STARTING"
    assert call("POST", "/api/sync") == (409, {"detail": "c'e' gia' una sincronizzazione in corso"})
    job = call("GET", "/api/sync")[1]["jobs"][0]
    assert (job["status"], job["scanned"], job["indexed"], job["deleted"], job["failed"]) == ("COMPLETE", 3, 2, 1, 0)


def test_sync_lambda_groups_events(fakes):
    _, agent, *_ = fakes
    event = sqs_event(s3_notification("uploads/a/a.pdf", "uploads/b/b c.pdf"), s3_notification("uploads/c/c.md"))
    assert sync.handler(event, None) == {"started": "JOB1", "files": 3}
    assert agent.started == ["3 file cambiati, es. uploads/a/a.pdf"]


def test_sync_lambda_retries_when_busy(fakes):
    """Con una sincronizzazione in corso la Lambda fallisce: SQS rimette i messaggi in coda."""
    _, agent, *_ = fakes
    agent.running = True
    with pytest.raises(sync.SyncBusy):
        sync.handler(sqs_event(s3_notification("uploads/a/a.pdf")), None)
    assert not agent.started


def test_sync_lambda_ignores_test_event(fakes):
    _, agent, *_ = fakes
    assert sync.handler(sqs_event({"Service": "Amazon S3", "Event": "s3:TestEvent"}), None) == {"started": None}
    assert not agent.started


def test_aws_error_is_readable(fakes, monkeypatch):
    _, _, runtime, _ = fakes

    def denied(**kw):
        raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "not authorized"}}, "Retrieve")
    monkeypatch.setattr(runtime, "retrieve", denied)
    code, body = call("POST", "/api/query", {"question": "prova"})
    assert code == 502 and body["detail"] == "errore AWS AccessDeniedException: not authorized"


def test_long_sync_description(fakes):
    _, agent, *_ = fakes
    sync.handler(sqs_event(s3_notification("uploads/x/" + "n" * 300 + ".txt")), None)
    assert len(agent.started[0]) == 200
