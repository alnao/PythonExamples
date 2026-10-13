"""
Logica comune delle Lambda della wiki: file di testo, parti per righe, embedding con Titan e
vettori su S3 Vectors. Nessun modello di chat: la ricerca restituisce i passaggi piu' simili.

Bucket dei file (FILES_BUCKET):
    files/<percorso>          file caricati dalla pagina o da upload_folder.py
    status/<percorso>.json    stato dell'indicizzazione (uploading | processing | ready | error)
Indice S3 Vectors (INDEX_ARN): un vettore per parte, chiave "<hash del percorso>#<00000>".
Metadati filtrabili: path, folder, extension, line_start, line_end; non filtrabile: text.
"""

import hashlib
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
FILES_BUCKET = os.environ.get("FILES_BUCKET", "")
INDEX_ARN = os.environ.get("INDEX_ARN", "")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
DIMENSIONS = 1024
MAX_FILE_KB = int(os.environ.get("MAX_FILE_KB", "1024"))
MAX_K = 100              # risultati per ricerca: una sola pagina di S3 Vectors
CHUNK_CHARS = 1500       # dimensione indicativa di una parte
OVERLAP_LINES = 3        # righe ripetute tra una parte e la successiva
TEXT_LIMIT = 4000        # caratteri salvati nel metadato text (S3 Vectors: 40 KB per vettore)

# File di testo indicizzati: per estensione o per nome
TEXT_EXTENSIONS = (".md", ".txt", ".py", ".js", ".ts", ".java", ".html", ".css", ".json", ".yaml", ".yml",
                   ".toml", ".ini", ".cfg", ".sh", ".bat", ".sql", ".xml", ".csv", ".tf", ".robot", ".example")
TEXT_NAMES = ("Dockerfile", "Makefile", "README", "LICENSE")

bedrock = boto3.client("bedrock-runtime", region_name=REGION,
                       config=Config(retries={"mode": "adaptive", "max_attempts": 10}))
# endpoint regionale: i POST prefirmati verso un bucket appena creato non ricevono redirect
s3 = boto3.client("s3", region_name=REGION, endpoint_url=f"https://s3.{REGION}.amazonaws.com",
                  config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
vectors = boto3.client("s3vectors", region_name=REGION)


class NotIndexable(Exception):
    """File che non si puo' indicizzare (formato, dimensione, contenuto binario)."""


# ----------------------------------------------------------------------
# File e parti
# ----------------------------------------------------------------------

def is_supported(path: str) -> bool:
    name = os.path.basename(path)
    return name.lower().endswith(TEXT_EXTENSIONS) or name in TEXT_NAMES


def describe_path(path: str) -> Dict:
    """Metadati filtrabili ricavati dal percorso (es. AWS/CDK/cdk05lambda/app.py)."""
    extension = os.path.splitext(path)[1].lower() or os.path.basename(path)
    return {"path": path, "folder": path.split("/", 1)[0] if "/" in path else "", "extension": extension}


def decode(data: bytes, path: str) -> str:
    if len(data) > MAX_FILE_KB * 1024:
        raise NotIndexable(f"{path}: {len(data) // 1024} KB, il massimo e' {MAX_FILE_KB} KB")
    if b"\x00" in data[:8192]:
        raise NotIndexable(f"{path}: sembra un file binario")
    return data.decode("utf-8", errors="replace")


def split_lines(text: str) -> List[Dict]:
    """
    Parti di circa CHUNK_CHARS caratteri che non spezzano le righe; ogni parte ripete le ultime
    OVERLAP_LINES righe della precedente e ricorda le sue righe di inizio e fine (contate da 1).
    """
    lines = text.splitlines()
    chunks, start = [], 0
    while start < len(lines):
        end, size = start, 0
        while end < len(lines) and (end == start or size + len(lines[end]) + 1 <= CHUNK_CHARS):
            size += len(lines[end]) + 1
            end += 1
        body = "\n".join(lines[start:end]).strip()
        if body:
            chunks.append({"text": body[:TEXT_LIMIT], "line_start": start + 1, "line_end": end})
        if end >= len(lines):
            break
        start = max(end - OVERLAP_LINES, start + 1)
    return chunks


# ----------------------------------------------------------------------
# Embedding
# ----------------------------------------------------------------------

def embed_one(text: str) -> List[float]:
    body = {"inputText": text, "dimensions": DIMENSIONS, "normalize": True}
    response = bedrock.invoke_model(modelId=EMBEDDING_MODEL, body=json.dumps(body),
                                    contentType="application/json", accept="application/json")
    return json.loads(response["body"].read())["embedding"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embedding Titan v2, 8 in parallelo."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(embed_one, texts))


def chunk_embedding_text(path: str, chunk: Dict) -> str:
    """Il percorso fa parte del testo dell'embedding: cosi' si trovano i file anche per nome."""
    return f"File: {path} (righe {chunk['line_start']}-{chunk['line_end']})\n{chunk['text']}"


# ----------------------------------------------------------------------
# Stato su S3 e vettori su S3 Vectors
# ----------------------------------------------------------------------

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def vector_key(path: str, chunk: int) -> str:
    """Chiave del vettore: hash del percorso (corto e senza caratteri speciali) e numero della parte."""
    return f"{hashlib.sha1(path.encode()).hexdigest()[:20]}#{chunk:05d}"


def status_key(path: str) -> str:
    return f"status/{path}.json"


def read_status(path: str) -> Dict:
    try:
        response = s3.get_object(Bucket=FILES_BUCKET, Key=status_key(path))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {}
        raise
    return json.loads(response["Body"].read())


def write_status(path: str, status: Dict):
    status = dict(status, path=path, updated=now())
    s3.put_object(Bucket=FILES_BUCKET, Key=status_key(path), Body=json.dumps(status).encode(),
                  ContentType="application/json")


def delete_status(path: str):
    s3.delete_object(Bucket=FILES_BUCKET, Key=status_key(path))


def list_statuses() -> List[Dict]:
    """Stato di tutti i file (letture in parallelo: con centinaia di file resta veloce)."""
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=FILES_BUCKET, Prefix="status/"):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))

    def read(key):
        return json.loads(s3.get_object(Bucket=FILES_BUCKET, Key=key)["Body"].read())
    with ThreadPoolExecutor(max_workers=32) as pool:
        return sorted(pool.map(read, keys), key=lambda s: s["path"])


def put_chunks(path: str, chunks: List[Dict], embeddings: List[List[float]]):
    """Scrive (o sovrascrive) i vettori delle parti, 500 per chiamata."""
    base = describe_path(path)
    items = [{"key": vector_key(path, i), "data": {"float32": embedding},
              "metadata": {**base, "line_start": c["line_start"], "line_end": c["line_end"], "text": c["text"]}}
             for i, (c, embedding) in enumerate(zip(chunks, embeddings))]
    for start in range(0, len(items), 500):
        vectors.put_vectors(indexArn=INDEX_ARN, vectors=items[start:start + 500])


def delete_chunks(path: str, numbers: Iterable[int]):
    keys = [vector_key(path, i) for i in numbers]
    for start in range(0, len(keys), 500):
        vectors.delete_vectors(indexArn=INDEX_ARN, keys=keys[start:start + 500])


def get_chunks(path: str, count: int) -> List[Dict]:
    """Parti di un file, 100 chiavi per chiamata."""
    keys = [vector_key(path, i) for i in range(count)]
    chunks = []
    for start in range(0, len(keys), 100):
        response = vectors.get_vectors(indexArn=INDEX_ARN, keys=keys[start:start + 100], returnMetadata=True)
        chunks.extend({"line_start": int(v["metadata"]["line_start"]), "line_end": int(v["metadata"]["line_end"]),
                       "text": v["metadata"]["text"]} for v in response.get("vectors", []))
    return sorted(chunks, key=lambda c: c["line_start"])


def build_filter(folder: str = "", extensions: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Filtro sui metadati: cartella con $startsWith sul percorso, estensioni con $in.
    Sugli indici ENHANCED (vector bucket creati dal 30/09/2026) il filtro si applica prima della
    ricerca, quindi i risultati sono sempre i piu' simili tra i file che rispettano il filtro.
    """
    conditions = []
    if folder.strip("/"):
        conditions.append({"path": {"$startsWith": folder.strip("/") + "/"}})
    if extensions:
        conditions.append({"extension": {"$in": [e.lower() for e in extensions]}})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def search(embedding: List[float], k: int, query_filter: Optional[Dict] = None) -> List[Dict]:
    """Le k parti piu' vicine alla domanda (distanza coseno), con metadati e distanza."""
    kwargs = {"filter": query_filter} if query_filter else {}
    response = vectors.query_vectors(indexArn=INDEX_ARN, topK=k, queryVector={"float32": embedding},
                                     returnMetadata=True, returnDistance=True, **kwargs)
    return response.get("vectors", [])
