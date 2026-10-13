"""
Lambda delle API della wiki (HTTP API Gateway, payload 2.0), raggiunta dal sito via CloudFront su /api/*.

Tutte le API tranne health e info richiedono l'header X-API-Key (segreto API_KEY_SECRET_ARN).
I percorsi dei file passano come parametro ?path=... (contengono "/").
"""

import base64
import hmac
import json
import os
import posixpath

import boto3
from botocore.exceptions import ClientError

import wiki

API_KEY_SECRET_ARN = os.environ.get("API_KEY_SECRET_ARN", "")
SNIPPETS_PER_FILE = 3

_api_key = {"value": None}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def api_key() -> str:
    if _api_key["value"] is None:
        secrets = boto3.client("secretsmanager", region_name=wiki.REGION)
        _api_key["value"] = secrets.get_secret_value(SecretId=API_KEY_SECRET_ARN)["SecretString"]
    return _api_key["value"]


def response(status: int, body) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def clean_path(value) -> str:
    """Percorso relativo normalizzato (niente "..", niente "/" iniziale)."""
    path = posixpath.normpath(str(value or "").strip().replace("\\", "/")).lstrip("/")
    if not path or path == "." or path.startswith("..") or len(path) > 500:
        raise HttpError(422, "percorso del file non valido")
    return path


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------

def health(body, params):
    return {"ok": True}


def info(body, params):
    return {"extensions": list(wiki.TEXT_EXTENSIONS), "names": list(wiki.TEXT_NAMES),
            "max_file_kb": wiki.MAX_FILE_KB, "max_k": wiki.MAX_K}


def search(body, params):
    """Passaggi piu' simili alla domanda, raggruppati per file (nessun modello di chat)."""
    question = str(body.get("question") or "").strip()
    if not question or len(question) > 2000:
        raise HttpError(422, "domanda obbligatoria (massimo 2000 caratteri)")
    try:
        k = int(body.get("k", 20))
    except (TypeError, ValueError):
        raise HttpError(422, "k deve essere un numero")
    if not 1 <= k <= wiki.MAX_K:
        raise HttpError(422, f"k deve essere tra 1 e {wiki.MAX_K}")
    extensions = body.get("extensions") or []
    if not isinstance(extensions, list):
        raise HttpError(422, "extensions deve essere una lista, es. [\".py\", \".md\"]")
    query_filter = wiki.build_filter(str(body.get("folder") or ""), extensions)
    found = wiki.search(wiki.embed_texts([question])[0], k, query_filter)

    files = {}
    for v in found:
        meta, score = v["metadata"], round(1 - v.get("distance", 0), 3)
        entry = files.setdefault(meta["path"], {"path": meta["path"], "folder": meta.get("folder", ""),
                                                "extension": meta.get("extension", ""), "score": score, "snippets": []})
        if len(entry["snippets"]) < SNIPPETS_PER_FILE:
            entry["snippets"].append({"line_start": int(meta["line_start"]), "line_end": int(meta["line_end"]),
                                      "score": score, "text": meta["text"]})
    return {"results": list(files.values()), "passages": len(found), "filter": query_filter}


def create_upload(body, params):
    """POST prefirmato per caricare un file in files/<percorso> (l'evento S3 lo indicizza)."""
    path = clean_path(body.get("path"))
    if not wiki.is_supported(path):
        raise HttpError(415, f"formato non supportato: {path} (solo file di testo)")
    previous = wiki.read_status(path)
    wiki.write_status(path, {"state": "uploading", "chunks": previous.get("chunks", 0)})
    upload = wiki.s3.generate_presigned_post(
        Bucket=wiki.FILES_BUCKET, Key=f"files/{path}",
        Conditions=[["content-length-range", 1, wiki.MAX_FILE_KB * 1024]],
        ExpiresIn=900,
    )
    return {"path": path, "upload": upload}


def list_files(body, params):
    return {"files": wiki.list_statuses()}


def file_status(body, params):
    path = clean_path(params.get("path"))
    status = wiki.read_status(path)
    if not status:
        raise HttpError(404, f"file {path} non trovato")
    return status


def file_chunks(body, params):
    status = file_status(body, params)
    chunks = wiki.get_chunks(status["path"], status.get("chunks", 0)) if status.get("state") == "ready" else []
    return dict(status, parts=chunks)


def delete_file(body, params):
    """Cancella il file da S3: l'evento ObjectRemoved toglie vettori e stato."""
    path = clean_path(params.get("path"))
    wiki.s3.delete_object(Bucket=wiki.FILES_BUCKET, Key=f"files/{path}")
    return {"status": "ok", "path": path}


def reindex(body, params):
    """Riscrive ogni file su se stesso: l'evento S3 rilancia l'indicizzazione."""
    keys = []
    for page in wiki.s3.get_paginator("list_objects_v2").paginate(Bucket=wiki.FILES_BUCKET, Prefix="files/"):
        keys.extend(obj["Key"] for obj in page.get("Contents", []) if not obj["Key"].endswith("/"))
    for key in keys:
        wiki.s3.copy_object(Bucket=wiki.FILES_BUCKET, Key=key, CopySource={"Bucket": wiki.FILES_BUCKET, "Key": key},
                            MetadataDirective="REPLACE")
    return {"queued": len(keys)}


# (metodo, percorso, funzione, richiede la chiave)
ROUTES = {
    ("GET", "/api/health"): (health, False),
    ("GET", "/api/info"): (info, False),
    ("POST", "/api/search"): (search, True),
    ("POST", "/api/uploads"): (create_upload, True),
    ("GET", "/api/files"): (list_files, True),
    ("GET", "/api/files/status"): (file_status, True),
    ("GET", "/api/files/parts"): (file_chunks, True),
    ("DELETE", "/api/files"): (delete_file, True),
    ("POST", "/api/reindex"): (reindex, True),
}


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    params = event.get("queryStringParameters") or {}
    try:
        if (method, path) not in ROUTES:
            raise HttpError(404, f"{method} {path} non esiste")
        function, protected = ROUTES[(method, path)]
        if protected and not hmac.compare_digest(headers.get("x-api-key", "").encode(), api_key().encode()):
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
        return response(200, function(body, params))
    except HttpError as e:
        return response(e.status, {"detail": str(e)})
    except ClientError as e:
        info_error = e.response.get("Error", {})
        wiki.logger.error(f"Errore AWS su {method} {path}: {info_error}")
        return response(502, {"detail": f"errore AWS {info_error.get('Code')}: {info_error.get('Message')}"})
    except Exception:
        wiki.logger.exception(f"Errore su {method} {path}")
        return response(500, {"detail": "errore interno, vedere i log della Lambda"})
