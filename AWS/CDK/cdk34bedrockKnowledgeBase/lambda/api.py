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

import kb

API_KEY_SECRET_ARN = os.environ.get("API_KEY_SECRET_ARN", "")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "50"))
DOC_ID = r"(?P<doc_id>[A-Za-z0-9_-]+)"
MODES = ("answer", "search")

_api_key = {"value": None}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def api_key() -> str:
    if _api_key["value"] is None:
        secrets = boto3.client("secretsmanager", region_name=kb.REGION)
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
        "formats": list(kb.SUPPORTED_EXTENSIONS),
        "notes": {"parser": "parser di default della Knowledge Base: solo il testo (niente OCR ne' immagini)",
                  "chat_model": kb.CHAT_MODEL_NAME},
        "max_upload_mb": MAX_UPLOAD_MB,
        "max_k": kb.MAX_K,
    }


def create_upload(body):
    """POST prefirmato per caricare il file su S3; l'evento S3 mette in coda la sincronizzazione.
    Gli altri file con lo stesso doc_id vengono cancellati: il nuovo file sostituisce il documento."""
    filename = os.path.basename(required_text(body, "filename", 200))
    if not filename.lower().endswith(kb.SUPPORTED_EXTENSIONS):
        raise HttpError(415, f"formato non supportato: {filename}")
    doc_id = kb.slugify(str(body.get("doc_id") or "").strip() or os.path.splitext(filename)[0])
    key = f"{kb.DOCS_PREFIX}{doc_id}/{filename}"
    kb.delete_keys(o["Key"] for o in kb.list_objects(f"{kb.DOCS_PREFIX}{doc_id}/") if o["Key"] != key)
    upload = kb.s3.generate_presigned_post(
        Bucket=kb.DOCS_BUCKET, Key=key,
        Conditions=[["content-length-range", 1, MAX_UPLOAD_MB * 1024 * 1024]],
        ExpiresIn=900,
    )
    return {"doc_id": doc_id, "key": key, "upload": upload}


def query(body):
    question = required_text(body, "question", 2000)
    try:
        k = int(body.get("k", 20))
    except (TypeError, ValueError):
        raise HttpError(422, "k deve essere un numero")
    if not 1 <= k <= kb.MAX_K:
        raise HttpError(422, f"k deve essere tra 1 e {kb.MAX_K}")
    mode = body.get("mode", "answer")
    if mode not in MODES:
        raise HttpError(422, f"mode deve essere uno tra {', '.join(MODES)}")
    found = kb.retrieve(question, k)
    sources = [{"n": f["n"], "doc_id": f["doc_id"], "filename": f["filename"], "page": f["page"],
                "score": f["score"], "excerpt": f["text"][:300]} for f in found]
    if not found:
        return {"answer": "Non ci sono ancora documenti indicizzati.", "sources": [], "found": 0}
    if mode == "search":
        # solo i brani, senza modello di chat (come la wiki del cdk32)
        return {"answer": None, "sources": sources, "found": len(found)}
    try:
        return {"answer": kb.answer(question, found), "sources": sources, "found": len(found)}
    except kb.ModelError as e:
        raise HttpError(502, str(e))


def list_documents(body):
    return {"documents": kb.documents()}


def document_status(body, doc_id):
    found = [d for d in kb.documents() if d["doc_id"] == doc_id]
    if not found:
        raise HttpError(404, f"documento {doc_id} non trovato")
    return found[0]


def forget(body, doc_id):
    """Cancella i file del documento: la sincronizzazione che segue toglie le sue parti dall'indice."""
    keys = [o["Key"] for o in kb.list_objects(f"{kb.DOCS_PREFIX}{doc_id}/")]
    if not keys:
        raise HttpError(404, f"documento {doc_id} non trovato")
    kb.delete_keys(keys)
    return {"status": "ok", "doc_id": doc_id, "deleted_files": len(keys)}


def list_syncs(body):
    return {"jobs": kb.sync_jobs()}


def start_sync(body):
    job = kb.start_sync("avviata dalla pagina admin")
    if job is None:
        raise HttpError(409, "c'e' gia' una sincronizzazione in corso")
    return job


# (metodo, percorso, funzione, richiede la chiave)
ROUTES = [
    ("GET", r"/api/health", health, False),
    ("GET", r"/api/supported-formats", supported_formats, False),
    ("POST", r"/api/uploads", create_upload, True),
    ("POST", r"/api/query", query, True),
    ("GET", r"/api/documents", list_documents, True),
    ("GET", rf"/api/documents/{DOC_ID}/status", document_status, True),
    ("DELETE", rf"/api/documents/{DOC_ID}", forget, True),
    ("GET", r"/api/sync", list_syncs, True),
    ("POST", r"/api/sync", start_sync, True),
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
        # errori di Bedrock o S3: codice e messaggio di AWS, leggibili nella pagina
        info = e.response.get("Error", {})
        kb.logger.error(f"Errore AWS su {method} {path}: {info}")
        return response(502, {"detail": f"errore AWS {info.get('Code')}: {info.get('Message')}"})
    except Exception:
        kb.logger.exception(f"Errore su {method} {path}")
        return response(500, {"detail": "errore interno, vedere i log della Lambda"})
