"""
Logica comune delle Lambda del Pocket RAG serverless: Bedrock, S3 Vectors, estrazione del
testo, chunking e stato dei documenti.

Bucket dei documenti (DOCS_BUCKET):
    uploads/<doc_id>/<file>   file originali, caricati dal browser con un POST prefirmato
    status/<doc_id>.json      stato dell'indicizzazione (processing | ready | error) e numero di parti
Indice S3 Vectors (INDEX_ARN): un vettore per parte con chiave "<doc_id>#<00000>" e metadati
doc_id, filename, chunk e text (il testo della parte, dichiarato non filtrabile nell'indice).
"""

import io
import json
import logging
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Iterable, List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "eu-central-1")
DOCS_BUCKET = os.environ.get("DOCS_BUCKET", "")
INDEX_ARN = os.environ.get("INDEX_ARN", "")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "eu.amazon.nova-lite-v1:0")
# vuoto = non inviare la temperature (i modelli Claude 5.x non la accettano)
CHAT_TEMPERATURE = os.environ.get("CHAT_TEMPERATURE", "0.2")
# modello multimodale per descrivere le immagini; vuoto = immagini non accettate (niente OCR qui)
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "eu.amazon.nova-lite-v1:0")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))
# brani al massimo per domanda e caratteri al massimo del contesto mandato al modello di chat:
# 600.000 caratteri sono circa 150.000 token (Nova Lite ne accetta 300.000) e restano nei 29
# secondi di API Gateway; i brani oltre il budget vengono trovati ma non usati
MAX_K = int(os.environ.get("MAX_K", "1000"))
CONTEXT_MAX_CHARS = int(os.environ.get("CONTEXT_MAX_CHARS", "600000"))
DIMENSIONS = 1024

# tentativi adattivi: con file grandi le migliaia di embedding possono superare la quota al secondo
bedrock = boto3.client("bedrock-runtime", region_name=REGION,
                       config=Config(retries={"mode": "adaptive", "max_attempts": 10}))
# endpoint regionale: i POST prefirmati verso un bucket appena creato non ricevono redirect
s3 = boto3.client("s3", region_name=REGION, endpoint_url=f"https://s3.{REGION}.amazonaws.com",
                  config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
vectors = boto3.client("s3vectors", region_name=REGION)

TEXT_EXTENSIONS = (".txt", ".md", ".csv", ".json", ".xml", ".html", ".css", ".js", ".py",
                   ".java", ".cpp", ".c", ".h")
OFFICE_EXTENSIONS = (".pdf", ".docx", ".xlsx", ".pptx")
# immagini accettate da Converse; .bmp e .tiff vengono convertite in PNG
IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".webp": "webp",
                 ".bmp": "png", ".tiff": "png", ".tif": "png"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS + OFFICE_EXTENSIONS + tuple(IMAGE_FORMATS)

IMAGE_PROMPT = ("Descrivi in italiano questa immagine in modo dettagliato. Trascrivi tutto il "
                "testo che contiene, poi descrivi il contenuto visivo (oggetti, persone, grafici, "
                "tabelle) in modo che la descrizione possa essere cercata e citata.")

SYSTEM_PROMPT = ("Sei un assistente che risponde a domande sui documenti caricati dall'utente. "
                 "Rispondi in italiano usando solo le informazioni del contesto. Cita le fonti "
                 "con il loro numero tra parentesi quadre, ad esempio [1] o [2][3]. Se il "
                 "contesto non contiene la risposta, dillo chiaramente invece di inventarla.")


class UnsupportedFile(Exception):
    """Formato del file non gestito."""


class ExtractionError(Exception):
    """Formato gestito ma testo non estraibile."""


# ----------------------------------------------------------------------
# Bedrock
# ----------------------------------------------------------------------

def converse_text(response: Dict) -> str:
    """Testo della risposta di Converse (salta i blocchi di ragionamento)."""
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(b["text"] for b in blocks if "text" in b).strip()
    if not text:
        raise ExtractionError(f"il modello non ha restituito testo (stopReason: {response.get('stopReason')})")
    return text


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
    return converse_text(response)


def embed_one(text: str) -> List[float]:
    body = {"inputText": text, "dimensions": DIMENSIONS, "normalize": True}
    response = bedrock.invoke_model(modelId=EMBEDDING_MODEL, body=json.dumps(body),
                                    contentType="application/json", accept="application/json")
    return json.loads(response["body"].read())["embedding"]


def embed_texts(texts: List[str], time_left=None) -> List[List[float]]:
    """
    Embedding Titan v2 (una chiamata per testo, 8 in parallelo, a blocchi di 64).
    time_left: funzione con i millisecondi rimasti alla Lambda; se mancano meno di 60 secondi
    ci si ferma con un errore chiaro invece di farsi interrompere dal timeout.
    """
    embeddings = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0, len(texts), 64):
            if time_left and time_left() < 60_000:
                raise ExtractionError(f"tempo esaurito dopo {start} parti su {len(texts)}: "
                                      "documento troppo grande per una sola indicizzazione")
            embeddings.extend(pool.map(embed_one, texts[start:start + 64]))
    return embeddings


def describe_image(data: bytes, extension: str) -> str:
    """Descrizione dell'immagine con il modello multimodale (IMAGE_MODEL)."""
    if not IMAGE_MODEL.strip():
        raise UnsupportedFile("immagini disattivate: IMAGE_MODEL vuoto")
    fmt = IMAGE_FORMATS[extension]
    if extension in (".bmp", ".tiff", ".tif"):
        from PIL import Image
        buffer = io.BytesIO()
        Image.open(io.BytesIO(data)).save(buffer, format="PNG")
        data = buffer.getvalue()
    response = bedrock.converse(
        modelId=IMAGE_MODEL,
        messages=[{"role": "user", "content": [
            {"image": {"format": fmt, "source": {"bytes": data}}},
            {"text": IMAGE_PROMPT},
        ]}],
        inferenceConfig={"maxTokens": 2000},
    )
    return converse_text(response)


# ----------------------------------------------------------------------
# Estrazione del testo (niente OCR: le pagine PDF senza testo vengono saltate)
# ----------------------------------------------------------------------

def extract_pdf(data: bytes, time_left=None) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for number, page in enumerate(reader.pages):
        if time_left and number % 20 == 0 and time_left() < 60_000:
            raise ExtractionError(f"tempo esaurito leggendo il PDF dopo {number} pagine su {len(reader.pages)}: "
                                  "documento troppo grande per una sola indicizzazione")
        pages.append((page.extract_text() or "").strip())
    skipped = sum(1 for p in pages if not p)
    if skipped:
        logger.info(f"PDF: {skipped} pagine senza testo saltate (OCR solo nella versione EC2)")
    return "\n\n".join(p for p in pages if p)


def extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def extract_xlsx(data: bytes) -> str:
    import openpyxl
    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts = []
    for sheet in workbook.worksheets:
        parts.append(f"Foglio: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                parts.append("\t".join("" if cell is None else str(cell) for cell in row))
        parts.append("")
    return "\n".join(parts)


def extract_pptx(data: bytes) -> str:
    from pptx import Presentation
    presentation = Presentation(io.BytesIO(data))
    parts = []
    for number, slide in enumerate(presentation.slides, start=1):
        parts.append(f"Slide {number}:")
        parts.extend(shape.text for shape in slide.shapes if getattr(shape, "text", "").strip())
        parts.append("")
    return "\n".join(parts)


def extract_text(data: bytes, filename: str, time_left=None) -> str:
    """Testo del file in base all'estensione (time_left: millisecondi rimasti alla Lambda)."""
    extension = os.path.splitext(filename.lower())[1]
    try:
        if extension in TEXT_EXTENSIONS:
            return data.decode("utf-8", errors="ignore")
        if extension in IMAGE_FORMATS:
            return describe_image(data, extension)
        if extension == ".pdf":
            return extract_pdf(data, time_left)
        if extension == ".docx":
            return extract_docx(data)
        if extension == ".xlsx":
            return extract_xlsx(data)
        if extension == ".pptx":
            return extract_pptx(data)
    except (ExtractionError, UnsupportedFile):
        raise
    except Exception as e:
        raise ExtractionError(f"impossibile leggere {filename}: {e}")
    raise UnsupportedFile(f"formato non supportato: {extension or filename}")


# ----------------------------------------------------------------------
# Chunking
# ----------------------------------------------------------------------

def split_long(paragraph: str, size: int) -> List[str]:
    """Spezza un paragrafo piu' lungo di size sulle frasi (e sulle parole se serve)."""
    if len(paragraph) <= size:
        return [paragraph]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?;:])\s+", paragraph):
        while len(sentence) > size:  # frase enorme: taglio sull'ultimo spazio
            cut = sentence.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + 1 + len(sentence) > size:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def overlap_tail(chunk: str, overlap: int) -> str:
    """Ultimi `overlap` caratteri del chunk, a partire da un inizio di parola."""
    if overlap <= 0 or len(chunk) <= overlap:
        return chunk if overlap > 0 else ""
    tail = chunk[-overlap:]
    space = tail.find(" ")
    return tail[space + 1:] if space >= 0 else tail


def split_text(text: str, size: int = None, overlap: int = None) -> List[str]:
    """Chunk di circa `size` caratteri sui paragrafi, ognuno ripete la coda del precedente."""
    size = size or CHUNK_SIZE
    overlap = CHUNK_OVERLAP if overlap is None else overlap
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        for piece in split_long(paragraph, size):
            if current and len(current) + 2 + len(piece) > size:
                chunks.append(current)
                tail = overlap_tail(current, overlap)
                current = f"{tail}\n\n{piece}" if tail else piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


# ----------------------------------------------------------------------
# Documenti: stato su S3 e vettori su S3 Vectors
# ----------------------------------------------------------------------

def slugify(value: str) -> str:
    """doc_id sicuro per chiavi S3 e chiavi dei vettori: lettere, numeri, - e _."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return value[:80] or "documento"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def vector_key(doc_id: str, chunk: int) -> str:
    return f"{doc_id}#{chunk:05d}"


def read_status(doc_id: str) -> Dict:
    try:
        response = s3.get_object(Bucket=DOCS_BUCKET, Key=f"status/{doc_id}.json")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return {}
        raise
    return json.loads(response["Body"].read())


def write_status(doc_id: str, status: Dict):
    status = dict(status, doc_id=doc_id, updated=now())
    s3.put_object(Bucket=DOCS_BUCKET, Key=f"status/{doc_id}.json",
                  Body=json.dumps(status).encode(), ContentType="application/json")


def list_statuses() -> List[Dict]:
    statuses = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=DOCS_BUCKET, Prefix="status/"):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=DOCS_BUCKET, Key=obj["Key"])["Body"].read()
            statuses.append(json.loads(body))
    return sorted(statuses, key=lambda s: s["doc_id"])


def list_keys(prefix: str) -> List[str]:
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=DOCS_BUCKET, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def delete_keys(keys: Iterable[str]):
    keys = list(keys)
    for start in range(0, len(keys), 1000):
        s3.delete_objects(Bucket=DOCS_BUCKET,
                          Delete={"Objects": [{"Key": k} for k in keys[start:start + 1000]]})


def put_chunks(doc_id: str, filename: str, chunks: List[str], embeddings: List[List[float]]):
    """Scrive (o sovrascrive) i vettori delle parti, 500 per chiamata."""
    items = [{"key": vector_key(doc_id, i), "data": {"float32": embedding},
              "metadata": {"doc_id": doc_id, "filename": filename, "chunk": i, "text": chunk}}
             for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))]
    for start in range(0, len(items), 500):
        vectors.put_vectors(indexArn=INDEX_ARN, vectors=items[start:start + 500])


def delete_chunks(doc_id: str, chunk_numbers: Iterable[int]):
    keys = [vector_key(doc_id, i) for i in chunk_numbers]
    for start in range(0, len(keys), 500):
        vectors.delete_vectors(indexArn=INDEX_ARN, keys=keys[start:start + 500])


def get_chunks(doc_id: str, count: int) -> List[Dict]:
    """Testo delle parti del documento, 100 chiavi per chiamata."""
    keys = [vector_key(doc_id, i) for i in range(count)]
    chunks = []
    for start in range(0, len(keys), 100):
        response = vectors.get_vectors(indexArn=INDEX_ARN, keys=keys[start:start + 100], returnMetadata=True)
        chunks.extend({"chunk": v["metadata"]["chunk"], "text": v["metadata"]["text"]}
                      for v in response.get("vectors", []))
    return sorted(chunks, key=lambda c: c["chunk"])


def search(embedding: List[float], k: int) -> List[Dict]:
    """Le k parti piu' vicine alla domanda (distanza coseno); S3 Vectors ne restituisce 100 per pagina."""
    found, token = [], None
    while True:
        kwargs = {"nextToken": token} if token else {}
        response = vectors.query_vectors(indexArn=INDEX_ARN, topK=k, queryVector={"float32": embedding},
                                         returnMetadata=True, returnDistance=True, **kwargs)
        found.extend(response.get("vectors", []))
        token = response.get("nextToken")
        if not token or len(found) >= k:
            return found[:k]
