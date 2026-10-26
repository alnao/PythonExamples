"""
Lambda delle API (HTTP API Gateway, payload 2.0), raggiunta dal sito tramite CloudFront su /api/*.

Tutte le API tranne health e supported-formats richiedono l'header X-API-Key, confrontato con
il segreto di Secrets Manager API_KEY_SECRET_ARN (letto una volta per container).
"""

import base64
import hmac
import json
import os
import re

import boto3
from botocore.exceptions import ClientError

import rag

API_KEY_SECRET_ARN = os.environ.get("API_KEY_SECRET_ARN", "")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
DOC_ID = r"(?P<doc_id>[A-Za-z0-9_-]+)"

_api_key = {"value": None}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def api_key() -> str:
    if _api_key["value"] is None:
        secrets = boto3.client("secretsmanager", region_name=rag.REGION)
        _api_key["value"] = secrets.get_secret_value(SecretId=API_KEY_SECRET_ARN)["SecretString"]
    return _api_key["value"]


def response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def required_text(body: dict, name: str, max_length: int) -> str:
    value = str(body.get(name) or "").strip()
    if not value or len(value) > max_length:
        raise HttpError(422, f"{name} obbligatorio (massimo {max_length} caratteri)")
    return value


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------

def health(body):
    return {"ok": True}


def supported_formats(body):
    return {
        "text_formats": list(rag.TEXT_EXTENSIONS),
        "document_formats": list(rag.OFFICE_EXTENSIONS),
        "image_formats": list(rag.IMAGE_FORMATS),
        "notes": {"pdf": "solo il testo con pypdf (nessun OCR nella versione serverless)",
                  "images": (f"descrizione generata da {rag.IMAGE_MODEL_NAME}" if rag.IMAGE_MODEL.strip()
                             else "disattivate (IMAGE_MODEL vuoto)")},
        "max_upload_mb": MAX_UPLOAD_MB,
        "max_k": rag.MAX_K,
    }


def create_upload(body):
    """POST prefirmato per caricare il file direttamente su S3 (l'evento avvia l'indicizzazione)."""
    filename = os.path.basename(required_text(body, "filename", 200))
    if not filename.lower().endswith(rag.SUPPORTED_EXTENSIONS):
        raise HttpError(415, f"formato non supportato: {filename}")
    doc_id = rag.slugify(str(body.get("doc_id") or "").strip() or os.path.splitext(filename)[0])
    key = f"uploads/{doc_id}/{filename}"
    # stato "uploading" (con le parti della versione precedente, da cancellare se serve):
    # la pagina aspetta che diventi ready o error
    previous = rag.read_status(doc_id)
    rag.write_status(doc_id, {"state": "uploading", "filename": filename, "chunks": previous.get("chunks", 0)})
    upload = rag.s3.generate_presigned_post(
        Bucket=rag.DOCS_BUCKET, Key=key,
        Conditions=[["content-length-range", 1, MAX_UPLOAD_MB * 1024 * 1024]],
        ExpiresIn=900,
    )
    return {"doc_id": doc_id, "key": key, "upload": upload}


def query(body):
    question = required_text(body, "question", 2000)
    try:
        k = int(body.get("k", 42))
    except (TypeError, ValueError):
        raise HttpError(422, "k deve essere un numero")
    if not 1 <= k <= rag.MAX_K:
        raise HttpError(422, f"k deve essere tra 1 e {rag.MAX_K}")
    found = rag.search(rag.embed_texts([question])[0], k)
    if not found:
        return {"answer": "Non ci sono ancora documenti indicizzati.", "sources": [], "found": 0, "used": 0}
    # i brani piu' simili entrano nel contesto finche' c'e' spazio (CONTEXT_MAX_CHARS)
    sources, blocks, size = [], [], 0
    for n, v in enumerate(found, start=1):
        meta = v["metadata"]
        block = f"[{n}] (file {meta['filename']}, parte {int(meta['chunk']) + 1})\n{meta['text']}"
        if blocks and size + len(block) > rag.CONTEXT_MAX_CHARS:
            break
        blocks.append(block)
        size += len(block) + 2
        sources.append({"n": n, "doc_id": meta["doc_id"], "filename": meta["filename"], "chunk": int(meta["chunk"]),
                        "score": round(1 - v.get("distance", 0), 3), "excerpt": meta["text"][:300]})
    context = "\n\n".join(blocks)
    try:
        answer = rag.chat(f"# Contesto\n{context}\n\n# Domanda\n{question}", system=rag.SYSTEM_PROMPT)
    except rag.ExtractionError as e:
        raise HttpError(502, str(e))
    return {"answer": answer, "sources": sources, "found": len(found), "used": len(sources)}


def generate(body):
    try:
        return {"answer": rag.chat(required_text(body, "prompt", 4000))}
    except rag.ExtractionError as e:
        raise HttpError(502, str(e))


def list_documents(body):
    return {"documents": rag.list_statuses()}


def document_status(body, doc_id):
    status = rag.read_status(doc_id)
    if not status:
        raise HttpError(404, f"documento {doc_id} non trovato")
    return status


def get_document(body, doc_id):
    status = document_status(body, doc_id)
    chunks = rag.get_chunks(doc_id, status.get("chunks", 0)) if status.get("state") == "ready" else []
    return dict(status, chunks=[{"chunk": int(c["chunk"]), "text": c["text"]} for c in chunks])


def forget(body, doc_id):
    """Fa dimenticare il documento: vettori, file originale e stato."""
    status = rag.read_status(doc_id)
    uploads = rag.list_keys(f"uploads/{doc_id}/")
    if not status and not uploads:
        raise HttpError(404, f"documento {doc_id} non trovato")
    if status.get("chunks"):
        rag.delete_chunks(doc_id, range(status["chunks"]))
    rag.delete_keys(uploads + ([f"status/{doc_id}.json"] if status else []))
    return {"status": "ok", "doc_id": doc_id, "deleted_chunks": status.get("chunks", 0)}


def reindex(body):
    """Riscrive ogni file di uploads/ su se stesso: l'evento S3 rilancia l'indicizzazione."""
    keys = [k for k in rag.list_keys("uploads/") if k.count("/") == 2 and not k.endswith("/")]
    for key in keys:
        rag.s3.copy_object(Bucket=rag.DOCS_BUCKET, Key=key, CopySource={"Bucket": rag.DOCS_BUCKET, "Key": key},
                           MetadataDirective="REPLACE")
    return {"queued": keys}


# (metodo, percorso, funzione, richiede la chiave)
ROUTES = [
    ("GET", r"/api/health", health, False),
    ("GET", r"/api/supported-formats", supported_formats, False),
    ("POST", r"/api/uploads", create_upload, True),
    ("POST", r"/api/query", query, True),
    ("POST", r"/api/generate", generate, True),
    ("GET", r"/api/documents", list_documents, True),
    ("GET", rf"/api/documents/{DOC_ID}/status", document_status, True),
    ("GET", rf"/api/documents/{DOC_ID}", get_document, True),
    ("DELETE", rf"/api/documents/{DOC_ID}", forget, True),
    ("POST", r"/api/reindex", reindex, True),
]


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    try:
        for route_method, pattern, function, protected in ROUTES:
            match = re.fullmatch(pattern, path)
            if match and route_method == method:
                break
        else:
            raise HttpError(404, f"{method} {path} non esiste")
        if protected:
            given = headers.get("x-api-key", "")
            if not hmac.compare_digest(given.encode(), api_key().encode()):
                raise HttpError(401, "API key mancante o errata")
        raw = event.get("body") or ""
        if raw and event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode()
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            raise HttpError(400, "il corpo della richiesta non e' JSON valido")
        if not isinstance(body, dict):
            raise HttpError(400, "il corpo della richiesta deve essere un oggetto JSON")
        return response(200, function(body, **match.groupdict()))
    except HttpError as e:
        return response(e.status, {"detail": str(e)})
    except ClientError as e:
        # errori di Bedrock, S3 o S3 Vectors: codice e messaggio di AWS, leggibili nella pagina
        info = e.response.get("Error", {})
        rag.logger.error(f"Errore AWS su {method} {path}: {info}")
        return response(502, {"detail": f"errore AWS {info.get('Code')}: {info.get('Message')}"})
    except Exception:
        rag.logger.exception(f"Errore su {method} {path}")
        return response(500, {"detail": "errore interno, vedere i log della Lambda"})
