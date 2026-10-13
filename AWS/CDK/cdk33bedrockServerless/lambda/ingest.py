"""
Lambda di indicizzazione: parte con l'evento S3 ObjectCreated su uploads/<doc_id>/<file>.

Estrae il testo, lo divide in parti, calcola gli embedding con Titan e li scrive su S3 Vectors;
lo stato (status/<doc_id>.json) passa da processing a ready o error. Un nuovo file con lo
stesso doc_id sostituisce il precedente (vettori in piu' e file con altro nome cancellati).
"""

import mimetypes
from urllib.parse import unquote_plus

import rag


def handler(event, context):
    time_left = context.get_remaining_time_in_millis if context else None
    for record in event.get("Records", []):
        process(unquote_plus(record["s3"]["object"]["key"]), time_left)


def process(key: str, time_left=None):
    parts = key.split("/", 2)
    if len(parts) != 3 or parts[0] != "uploads" or not parts[2]:
        rag.logger.info(f"Chiave ignorata: {key}")
        return
    doc_id, filename = parts[1], parts[2]
    previous = rag.read_status(doc_id)
    old_chunks = previous.get("chunks", 0)
    rag.write_status(doc_id, {"state": "processing", "filename": filename, "chunks": old_chunks})
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        data = rag.s3.get_object(Bucket=rag.DOCS_BUCKET, Key=key)["Body"].read()
        text = rag.extract_text(data, filename, time_left)
        chunks = rag.split_text(text)
        if not chunks:
            raise rag.ExtractionError(f"nessun testo trovato in {filename}")
        rag.put_chunks(doc_id, filename, chunks, rag.embed_texts(chunks, time_left))
    except (rag.UnsupportedFile, rag.ExtractionError) as e:
        fail(doc_id, filename, content_type, old_chunks, str(e))
        return
    except Exception as e:
        rag.logger.exception(f"Errore indicizzando {key}")
        fail(doc_id, filename, content_type, old_chunks, f"errore interno: {e}")
        return
    if old_chunks > len(chunks):
        rag.delete_chunks(doc_id, range(len(chunks), old_chunks))
    rag.delete_keys(k for k in rag.list_keys(f"uploads/{doc_id}/") if k != key)
    rag.write_status(doc_id, {"state": "ready", "filename": filename, "content_type": content_type,
                              "chunks": len(chunks), "text_length": len(text)})
    rag.logger.info(f"Indicizzato {key}: {len(chunks)} parti")


def fail(doc_id: str, filename: str, content_type: str, old_chunks: int, error: str):
    """Documento non leggibile: niente vettori (nemmeno quelli della versione precedente)."""
    if old_chunks:
        rag.delete_chunks(doc_id, range(old_chunks))
    rag.write_status(doc_id, {"state": "error", "filename": filename, "content_type": content_type,
                              "chunks": 0, "error": error})
    rag.logger.warning(f"{doc_id}/{filename} non indicizzato: {error}")
