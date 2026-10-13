"""
Pocket RAG su EC2: FastAPI + ChromaDB locale + Amazon Bedrock (Converse API) + S3.

- le API sono sotto /api, il sito (cartella web/) e' servito dallo stesso processo su /
- i documenti originali stanno su S3 in uploads/<doc_id>/<nome file>
- chunk, embedding e metadati stanno in ChromaDB (cartella CHROMA_DIR); dopo ogni modifica
  l'indice viene salvato su S3 (CHROMA_BACKUP_KEY) e ripristinato all'avvio se la cartella
  locale e' vuota; /api/reindex lo ricostruisce dai file su S3
- tutte le API tranne /api/health richiedono l'header X-API-Key

Configurazione in .env (vedi .env.example).
"""

import hmac
import io
import json
import logging
import mimetypes
import os
import re
import tarfile
import tempfile
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

import boto3
import chromadb
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("pocket-rag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    AWS_REGION: str = "eu-central-1"
    S3_BUCKET: str = "bedrock-alnao-bucket"
    CHROMA_DIR: str = str(BASE_DIR / "chroma")
    CHROMA_BACKUP_KEY: str = "index/chroma.tar.gz"
    EMBEDDING_MODEL: str = "amazon.titan-embed-text-v2:0"
    CHAT_MODEL: str = "eu.amazon.nova-lite-v1:0"
    # vuoto = non inviare la temperature (i modelli Claude 5.x non la accettano)
    CHAT_TEMPERATURE: str = "0.2"
    # modello multimodale per descrivere le immagini; vuoto = OCR locale con Tesseract (gratis, solo il testo)
    IMAGE_MODEL: str = "eu.amazon.nova-lite-v1:0"
    API_KEY: str = ""            # chiave diretta, comoda in locale
    API_KEY_PARAMETER: str = ""  # oppure nome del parametro SSM SecureString (EC2)
    ALLOWED_ORIGINS: str = ""    # CORS, separati da virgola; vuoto = solo stessa origine
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_MB: int = 20


settings = Settings()

bedrock = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)
s3 = boto3.client("s3", region_name=settings.AWS_REGION)

# stato del processo: chiave API e collection Chroma (impostati all'avvio)
state = {"api_key": "", "collection": None}
# un solo writer alla volta su Chroma e sul backup
write_lock = threading.Lock()

TEXT_EXTENSIONS = (".txt", ".md", ".csv", ".json", ".xml", ".html", ".css", ".js", ".py",
                   ".java", ".cpp", ".c", ".h")
OFFICE_EXTENSIONS = (".pdf", ".docx", ".xlsx", ".pptx")
# immagini accettate da Converse; .bmp e .tiff vengono convertite in PNG
IMAGE_FORMATS = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".webp": "webp",
                 ".bmp": "png", ".tiff": "png", ".tif": "png"}

IMAGE_PROMPT = ("Descrivi in italiano questa immagine in modo dettagliato. Trascrivi tutto il "
                "testo che contiene, poi descrivi il contenuto visivo (oggetti, persone, grafici, "
                "tabelle) in modo che la descrizione possa essere cercata e citata.")

SYSTEM_PROMPT = ("Sei un assistente che risponde a domande sui documenti caricati dall'utente. "
                 "Rispondi in italiano usando solo le informazioni del contesto. Cita le fonti "
                 "con il loro numero tra parentesi quadre, ad esempio [1] o [2][3]. Se il "
                 "contesto non contiene la risposta, dillo chiaramente invece di inventarla.")


class UnsupportedFile(Exception):
    """Formato del file non gestito (risposta 415)."""


class ExtractionError(Exception):
    """Formato gestito ma testo non estraibile (risposta 422)."""


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
    if settings.CHAT_TEMPERATURE.strip():
        inference["temperature"] = float(settings.CHAT_TEMPERATURE)
    kwargs = {"system": [{"text": system}]} if system else {}
    response = bedrock.converse(
        modelId=settings.CHAT_MODEL,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig=inference,
        **kwargs,
    )
    return converse_text(response)


def embed_one(text: str) -> List[float]:
    body = {"inputText": text, "dimensions": 1024, "normalize": True}
    response = bedrock.invoke_model(modelId=settings.EMBEDDING_MODEL, body=json.dumps(body),
                                    contentType="application/json", accept="application/json")
    return json.loads(response["body"].read())["embedding"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embedding Titan v2 (una chiamata per testo, 4 in parallelo)."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(embed_one, texts))


def describe_image(data: bytes, extension: str) -> str:
    """Descrizione dell'immagine con il modello multimodale (IMAGE_MODEL) o, se vuoto, OCR locale."""
    if not settings.IMAGE_MODEL.strip():
        return ocr_image(data)
    fmt = IMAGE_FORMATS[extension]
    if extension in (".bmp", ".tiff", ".tif"):
        from PIL import Image
        buffer = io.BytesIO()
        Image.open(io.BytesIO(data)).save(buffer, format="PNG")
        data = buffer.getvalue()
    response = bedrock.converse(
        modelId=settings.IMAGE_MODEL,
        messages=[{"role": "user", "content": [
            {"image": {"format": fmt, "source": {"bytes": data}}},
            {"text": IMAGE_PROMPT},
        ]}],
        inferenceConfig={"maxTokens": 2000},
    )
    return converse_text(response)


def ocr_image(data: bytes) -> str:
    """Testo dell'immagine con Tesseract: gratis, ma niente descrizione del contenuto visivo."""
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(io.BytesIO(data)), lang="ita+eng").strip()
    except Exception as e:  # pytesseract o tesseract mancanti
        raise ExtractionError(f"OCR dell'immagine non riuscito: {e}")
    if not text:
        raise ExtractionError("nessun testo trovato nell'immagine (con IMAGE_MODEL vuoto si usa solo l'OCR)")
    return text


# ----------------------------------------------------------------------
# Estrazione del testo
# ----------------------------------------------------------------------

def extract_pdf(data: bytes) -> str:
    """Testo delle pagine con PyPDF; OCR (Tesseract) solo per le pagine senza testo."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            text = ocr_pdf_page(data, number)
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def ocr_pdf_page(data: bytes, number: int) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.warning("OCR non disponibile (pytesseract/pdf2image non installati)")
        return ""
    try:
        images = convert_from_bytes(data, first_page=number, last_page=number)
        return "\n".join(pytesseract.image_to_string(img, lang="ita+eng") for img in images).strip()
    except Exception as e:  # tesseract o poppler mancanti
        logger.warning(f"OCR fallito sulla pagina {number}: {e}")
        return ""


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


def extract_text(data: bytes, filename: str) -> str:
    """Testo del file in base all'estensione."""
    extension = os.path.splitext(filename.lower())[1]
    try:
        if extension in TEXT_EXTENSIONS:
            return data.decode("utf-8", errors="ignore")
        if extension in IMAGE_FORMATS:
            return describe_image(data, extension)
        if extension == ".pdf":
            return extract_pdf(data)
        if extension == ".docx":
            return extract_docx(data)
        if extension == ".xlsx":
            return extract_xlsx(data)
        if extension == ".pptx":
            return extract_pptx(data)
    except ExtractionError:
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
    size = size or settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP if overlap is None else overlap
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
# Documenti (Chroma + S3)
# ----------------------------------------------------------------------

def slugify(value: str) -> str:
    """doc_id sicuro per chiavi S3 e ID Chroma: lettere, numeri, - e _."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return value[:80] or "documento"


def collection():
    return state["collection"]


def delete_s3_prefix(prefix: str):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=settings.S3_BUCKET, Delete={"Objects": keys})


def index_document(doc_id: str, filename: str, content_type: str, text: str) -> int:
    """Sostituisce i chunk del documento con quelli del testo; restituisce quanti sono."""
    chunks = split_text(text)
    if not chunks:
        raise ExtractionError(f"nessun testo trovato in {filename}")
    embeddings = embed_texts(chunks)
    collection().delete(where={"doc_id": doc_id})
    collection().add(
        ids=[f"{doc_id}#{i:05d}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id, "filename": filename, "content_type": content_type, "chunk": i}
                   for i in range(len(chunks))],
    )
    return len(chunks)


def backup_index():
    """Salva la cartella di Chroma su S3 come tar.gz."""
    with tempfile.TemporaryFile() as tmp:
        with tarfile.open(fileobj=tmp, mode="w:gz") as tar:
            tar.add(settings.CHROMA_DIR, arcname=".")
        tmp.seek(0)
        s3.upload_fileobj(tmp, settings.S3_BUCKET, settings.CHROMA_BACKUP_KEY)
    logger.info(f"Indice salvato su s3://{settings.S3_BUCKET}/{settings.CHROMA_BACKUP_KEY}")


def restore_index():
    """Ripristina l'indice da S3 se la cartella locale e' vuota e il backup esiste."""
    directory = Path(settings.CHROMA_DIR)
    if directory.exists() and any(directory.iterdir()):
        return
    directory.mkdir(parents=True, exist_ok=True)
    try:
        response = s3.get_object(Bucket=settings.S3_BUCKET, Key=settings.CHROMA_BACKUP_KEY)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            logger.info("Nessun backup dell'indice su S3: si parte da un indice vuoto")
            return
        raise
    with tarfile.open(fileobj=io.BytesIO(response["Body"].read()), mode="r:gz") as tar:
        tar.extractall(directory, filter="data")
    logger.info("Indice ripristinato dal backup su S3")


def load_api_key() -> str:
    if settings.API_KEY:
        return settings.API_KEY
    if settings.API_KEY_PARAMETER:
        ssm = boto3.client("ssm", region_name=settings.AWS_REGION)
        return ssm.get_parameter(Name=settings.API_KEY_PARAMETER, WithDecryption=True)["Parameter"]["Value"]
    logger.warning("Nessuna API key configurata (API_KEY o API_KEY_PARAMETER): le API rispondono 503")
    return ""


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    state["api_key"] = load_api_key()
    restore_index()
    client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    state["collection"] = client.get_or_create_collection(name="docs", metadata={"hnsw:space": "cosine"})
    yield


def require_api_key(x_api_key: str = Header(default="")):
    if not state["api_key"]:
        raise HTTPException(503, "API key non configurata sul server")
    if not hmac.compare_digest(x_api_key.encode(), state["api_key"].encode()):
        raise HTTPException(401, "API key mancante o errata")


app = FastAPI(title="Pocket RAG", lifespan=lifespan)


@app.exception_handler(ClientError)
async def aws_error(request: Request, error: ClientError):
    """Errori di Bedrock, S3 o SSM: 502 con codice e messaggio di AWS, leggibili nella pagina."""
    info = error.response.get("Error", {})
    logger.error(f"Errore AWS su {request.url.path}: {info}")
    return JSONResponse(status_code=502, content={"detail": f"errore AWS {info.get('Code')}: {info.get('Message')}"})

if settings.ALLOWED_ORIGINS.strip():
    app.add_middleware(CORSMiddleware,
                       allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["*"])

public = APIRouter(prefix="/api")
api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=4, ge=1, le=10)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


@public.get("/health")
def health():
    return {"ok": True}


@public.get("/supported-formats")
def supported_formats():
    return {
        "text_formats": list(TEXT_EXTENSIONS),
        "document_formats": list(OFFICE_EXTENSIONS),
        "image_formats": list(IMAGE_FORMATS),
        "notes": {
            "pdf": "testo con pypdf, OCR con Tesseract solo per le pagine senza testo",
            "images": (f"descrizione generata da {settings.IMAGE_MODEL}" if settings.IMAGE_MODEL.strip()
                       else "solo il testo, letto con l'OCR di Tesseract"),
        },
    }


@api.post("/ingest")
def ingest(file: UploadFile = File(...), doc_id: str = Form(default="")):
    data = file.file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"file oltre {settings.MAX_UPLOAD_MB} MB")
    filename = os.path.basename(file.filename or "documento")
    doc_id = slugify(doc_id or os.path.splitext(filename)[0])
    content_type = mimetypes.guess_type(filename)[0] or file.content_type or "application/octet-stream"
    try:
        text = extract_text(data, filename)
        with write_lock:
            chunks = index_document(doc_id, filename, content_type, text)
            delete_s3_prefix(f"uploads/{doc_id}/")
            s3.put_object(Bucket=settings.S3_BUCKET, Key=f"uploads/{doc_id}/{filename}",
                          Body=data, ContentType=content_type)
            backup_index()
    except UnsupportedFile as e:
        raise HTTPException(415, str(e))
    except ExtractionError as e:
        raise HTTPException(422, str(e))
    return {"doc_id": doc_id, "filename": filename, "content_type": content_type,
            "extracted_text_length": len(text), "chunks": chunks}


@api.post("/query")
def query(request: QueryRequest):
    if collection().count() == 0:
        return {"answer": "Non ci sono ancora documenti indicizzati.", "sources": []}
    embedding = embed_texts([request.question])[0]
    result = collection().query(query_embeddings=[embedding], n_results=request.k,
                                include=["documents", "metadatas", "distances"])
    sources = []
    for n, (doc, meta, distance) in enumerate(zip(result["documents"][0], result["metadatas"][0],
                                                  result["distances"][0]), start=1):
        sources.append({"n": n, "doc_id": meta["doc_id"], "filename": meta["filename"],
                        "chunk": meta["chunk"], "score": round(1 - distance, 3), "text": doc})
    context = "\n\n".join(f"[{s['n']}] (file {s['filename']}, parte {s['chunk'] + 1})\n{s['text']}"
                          for s in sources)
    try:
        answer = chat(f"# Contesto\n{context}\n\n# Domanda\n{request.question}", system=SYSTEM_PROMPT)
    except ExtractionError as e:
        raise HTTPException(502, str(e))
    for s in sources:
        s["excerpt"] = s.pop("text")[:300]
    return {"answer": answer, "sources": sources}


@api.post("/generate")
def generate(request: GenerateRequest):
    try:
        return {"answer": chat(request.prompt)}
    except ExtractionError as e:
        raise HTTPException(502, str(e))


@api.get("/documents")
def list_documents():
    documents = {}
    for meta in collection().get(include=["metadatas"])["metadatas"]:
        doc = documents.setdefault(meta["doc_id"], {"doc_id": meta["doc_id"], "filename": meta["filename"],
                                                    "content_type": meta["content_type"], "chunks": 0})
        doc["chunks"] += 1
    return {"documents": sorted(documents.values(), key=lambda d: d["doc_id"])}


@api.get("/documents/{doc_id}")
def get_document(doc_id: str):
    result = collection().get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    if not result["ids"]:
        raise HTTPException(404, f"documento {doc_id} non trovato")
    chunks = sorted(({"chunk": m["chunk"], "text": d} for d, m in zip(result["documents"], result["metadatas"])),
                    key=lambda c: c["chunk"])
    meta = result["metadatas"][0]
    return {"doc_id": doc_id, "filename": meta["filename"], "content_type": meta["content_type"], "chunks": chunks}


@api.delete("/documents/{doc_id}")
def forget(doc_id: str):
    """Fa dimenticare il documento: chunk, embedding e file originale su S3."""
    with write_lock:
        ids = collection().get(where={"doc_id": doc_id})["ids"]
        if not ids:
            raise HTTPException(404, f"documento {doc_id} non trovato")
        collection().delete(ids=ids)
        delete_s3_prefix(f"uploads/{doc_id}/")
        backup_index()
    return {"status": "ok", "doc_id": doc_id, "deleted_chunks": len(ids)}


@api.post("/reindex")
def reindex():
    """Ricostruisce l'indice da tutti i file in uploads/ (dopo una perdita dell'indice)."""
    indexed, errors = [], []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix="uploads/"):
        for obj in page.get("Contents", []):
            parts = obj["Key"].split("/", 2)
            if len(parts) != 3 or not parts[2]:
                continue
            doc_id, filename = parts[1], parts[2]
            try:
                data = s3.get_object(Bucket=settings.S3_BUCKET, Key=obj["Key"])["Body"].read()
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                text = extract_text(data, filename)
                with write_lock:
                    chunks = index_document(doc_id, filename, content_type, text)
                indexed.append({"doc_id": doc_id, "filename": filename, "chunks": chunks})
            except (UnsupportedFile, ExtractionError) as e:
                errors.append({"key": obj["Key"], "error": str(e)})
    with write_lock:
        backup_index()
    return {"indexed": indexed, "errors": errors}


app.include_router(public)
app.include_router(api)
app.mount("/", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")
