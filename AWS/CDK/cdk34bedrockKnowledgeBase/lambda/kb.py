"""
Logica comune delle Lambda del RAG con Bedrock Knowledge Base: documenti su S3, sincronizzazione,
ricerca dei brani (Retrieve) e risposta del modello di chat (Converse).

Bucket dei documenti (DOCS_BUCKET):
    uploads/<doc_id>/<file>   file originali, sorgente della Knowledge Base
L'indice (S3 Vectors) e le parti sono gestiti dalla Knowledge Base: qui non si leggono ne' scrivono vettori.
"""

import logging
import os
import re
import unicodedata
from typing import Dict, Iterable, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
DOCS_BUCKET = os.environ.get("DOCS_BUCKET", "")
DOCS_PREFIX = os.environ.get("DOCS_PREFIX", "uploads/")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID", "")
# nello stack e' l'ARN del profilo di inferenza con i tag; CHAT_MODEL_NAME e' il nome da mostrare
CHAT_MODEL = os.environ.get("CHAT_MODEL", "eu.amazon.nova-lite-v1:0")
CHAT_MODEL_NAME = os.environ.get("CHAT_MODEL_NAME", CHAT_MODEL)
CHAT_TEMPERATURE = os.environ.get("CHAT_TEMPERATURE", "0.2")
# la Knowledge Base restituisce al massimo 100 brani per Retrieve
MAX_K = 100

# formati letti dal parser di default della Knowledge Base (solo il testo: niente OCR ne' immagini)
SUPPORTED_EXTENSIONS = (".txt", ".md", ".html", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".pdf")

SYSTEM_PROMPT = ("Sei un assistente che risponde a domande sui documenti caricati dall'utente. "
                 "Rispondi in italiano usando solo le informazioni del contesto. Cita le fonti "
                 "con il loro numero tra parentesi quadre, ad esempio [1] o [2][3]. Se il "
                 "contesto non contiene la risposta, dillo chiaramente invece di inventarla.")

bedrock = boto3.client("bedrock-runtime", region_name=REGION,
                       config=Config(retries={"mode": "adaptive", "max_attempts": 5}))
agent = boto3.client("bedrock-agent", region_name=REGION)
agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
# endpoint regionale: i POST prefirmati verso un bucket appena creato non ricevono redirect
s3 = boto3.client("s3", region_name=REGION, endpoint_url=f"https://s3.{REGION}.amazonaws.com",
                  config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))


class ModelError(Exception):
    """Il modello non ha restituito una risposta utilizzabile."""


# ----------------------------------------------------------------------
# Documenti su S3
# ----------------------------------------------------------------------

def slugify(value: str) -> str:
    """doc_id sicuro per le chiavi S3: lettere, numeri, - e _."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return value[:80] or "documento"


def list_objects(prefix: str = None) -> List[Dict]:
    objects = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=DOCS_BUCKET, Prefix=prefix or DOCS_PREFIX):
        objects.extend(page.get("Contents", []))
    return objects


def delete_keys(keys: Iterable[str]):
    keys = list(keys)
    for start in range(0, len(keys), 1000):
        s3.delete_objects(Bucket=DOCS_BUCKET,
                          Delete={"Objects": [{"Key": k} for k in keys[start:start + 1000]]})


def source_uri(key: str) -> str:
    return f"s3://{DOCS_BUCKET}/{key}"


def key_from_uri(uri: str) -> str:
    return uri.split("/", 3)[3] if uri.count("/") >= 3 else uri


def split_key(key: str) -> Optional[Dict]:
    """uploads/<doc_id>/<file> -> doc_id e nome del file (None per le chiavi fuori schema)."""
    parts = key[len(DOCS_PREFIX):].split("/", 1) if key.startswith(DOCS_PREFIX) else []
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return {"doc_id": parts[0], "filename": parts[1]}


# ----------------------------------------------------------------------
# Knowledge Base: stato dei documenti e sincronizzazioni
# ----------------------------------------------------------------------

def kb_documents() -> Dict[str, Dict]:
    """Stato di ogni documento visto dalla Knowledge Base, per URI S3."""
    statuses, token = {}, None
    while True:
        kwargs = {"nextToken": token} if token else {}
        response = agent.list_knowledge_base_documents(knowledgeBaseId=KNOWLEDGE_BASE_ID,
                                                       dataSourceId=DATA_SOURCE_ID, maxResults=1000, **kwargs)
        for d in response.get("documentDetails", []):
            uri = d.get("identifier", {}).get("s3", {}).get("uri", "")
            statuses[uri] = {"status": d.get("status", ""), "reason": d.get("statusReason", ""),
                             "updated": iso(d.get("updatedAt"))}
        token = response.get("nextToken")
        if not token:
            return statuses


def documents() -> List[Dict]:
    """File del bucket con lo stato della Knowledge Base; NOT_SYNCED = non ancora visto da una sincronizzazione."""
    statuses = kb_documents()
    result = []
    for obj in list_objects():
        names = split_key(obj["Key"])
        if not names:
            continue
        kb_status = statuses.get(source_uri(obj["Key"]), {"status": "NOT_SYNCED", "reason": "", "updated": ""})
        result.append(dict(names, key=obj["Key"], size=obj.get("Size", 0),
                           uploaded=iso(obj.get("LastModified")), **kb_status))
    return sorted(result, key=lambda d: (d["doc_id"], d["filename"]))


def start_sync(description: str) -> Optional[Dict]:
    """Avvia una sincronizzazione (incrementale); None se ce n'e' gia' una in corso."""
    try:
        job = agent.start_ingestion_job(knowledgeBaseId=KNOWLEDGE_BASE_ID, dataSourceId=DATA_SOURCE_ID,
                                        description=description[:200])["ingestionJob"]
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConflictException":
            return None
        raise
    return job_summary(job)


def sync_jobs(limit: int = 10) -> List[Dict]:
    response = agent.list_ingestion_jobs(knowledgeBaseId=KNOWLEDGE_BASE_ID, dataSourceId=DATA_SOURCE_ID,
                                         sortBy={"attribute": "STARTED_AT", "order": "DESCENDING"},
                                         maxResults=limit)
    return [job_summary(j) for j in response.get("ingestionJobSummaries", [])]


def job_summary(job: Dict) -> Dict:
    stats = job.get("statistics", {})
    return {"id": job.get("ingestionJobId"), "status": job.get("status"), "description": job.get("description", ""),
            "started": iso(job.get("startedAt")), "updated": iso(job.get("updatedAt")),
            "scanned": stats.get("numberOfDocumentsScanned", 0),
            "indexed": stats.get("numberOfNewDocumentsIndexed", 0) + stats.get("numberOfModifiedDocumentsIndexed", 0),
            "deleted": stats.get("numberOfDocumentsDeleted", 0),
            "failed": stats.get("numberOfDocumentsFailed", 0)}


def iso(value) -> str:
    return value.isoformat(timespec="seconds") if hasattr(value, "isoformat") else str(value or "")


# ----------------------------------------------------------------------
# Ricerca e risposta
# ----------------------------------------------------------------------

def retrieve(question: str, k: int) -> List[Dict]:
    """I k brani piu' simili alla domanda: embedding della domanda e ricerca li fa la Knowledge Base."""
    response = agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": k}},
    )
    found = []
    for n, r in enumerate(response.get("retrievalResults", []), start=1):
        key = key_from_uri(r.get("location", {}).get("s3Location", {}).get("uri", ""))
        names = split_key(key) or {"doc_id": "", "filename": key}
        page = r.get("metadata", {}).get("x-amz-bedrock-kb-document-page-number")
        found.append(dict(names, n=n, text=r.get("content", {}).get("text", ""),
                          score=round(float(r.get("score", 0)), 3), page=int(page) if page else None))
    return found


def chat(prompt: str, system: str = "") -> str:
    """Una domanda al modello di chat (CHAT_MODEL) con la Converse API."""
    inference = {"maxTokens": 1024}
    if CHAT_TEMPERATURE.strip():
        inference["temperature"] = float(CHAT_TEMPERATURE)
    kwargs = {"system": [{"text": system}]} if system else {}
    response = bedrock.converse(
        modelId=CHAT_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig=inference,
        **kwargs,
    )
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(b["text"] for b in blocks if "text" in b).strip()
    if not text:
        raise ModelError(f"il modello non ha restituito testo (stopReason: {response.get('stopReason')})")
    return text


def answer(question: str, found: List[Dict]) -> str:
    """Risposta con le fonti numerate [n] come contesto."""
    blocks = []
    for f in found:
        where = f"file {f['filename']}" + (f", pagina {f['page']}" if f["page"] else "")
        blocks.append(f"[{f['n']}] ({where})\n{f['text']}")
    context = "\n\n".join(blocks)
    return chat(f"# Contesto\n{context}\n\n# Domanda\n{question}", system=SYSTEM_PROMPT)
