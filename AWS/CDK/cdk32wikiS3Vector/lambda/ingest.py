"""
Lambda di indicizzazione, attivata dagli eventi S3 su files/<percorso>:
- ObjectCreated: legge il file, lo divide in parti per righe, calcola gli embedding con Titan e
  scrive i vettori (un file caricato di nuovo sostituisce il precedente)
- ObjectRemoved: cancella i vettori e lo stato del file
"""

from urllib.parse import unquote_plus

import wiki


def handler(event, context):
    for record in event.get("Records", []):
        key = unquote_plus(record["s3"]["object"]["key"])
        if not key.startswith("files/") or key.endswith("/"):
            wiki.logger.info(f"Chiave ignorata: {key}")
            continue
        path = key[len("files/"):]
        if record.get("eventName", "").startswith("ObjectRemoved"):
            remove(path)
        else:
            index(path, key)


def remove(path: str):
    status = wiki.read_status(path)
    if status.get("chunks"):
        wiki.delete_chunks(path, range(status["chunks"]))
    if status:
        wiki.delete_status(path)
    wiki.logger.info(f"Rimosso {path}: {status.get('chunks', 0)} parti")


def index(path: str, key: str):
    old_chunks = wiki.read_status(path).get("chunks", 0)
    wiki.write_status(path, {"state": "processing", "chunks": old_chunks})
    try:
        obj = wiki.s3.get_object(Bucket=wiki.FILES_BUCKET, Key=key)
        if not wiki.is_supported(path):
            raise wiki.NotIndexable(f"{path}: formato non supportato")
        text = wiki.decode(obj["Body"].read(), path)
        chunks = wiki.split_lines(text)
        if not chunks:
            raise wiki.NotIndexable(f"{path}: file vuoto")
        embeddings = wiki.embed_texts([wiki.chunk_embedding_text(path, c) for c in chunks])
        wiki.put_chunks(path, chunks, embeddings)
    except Exception as e:
        if not isinstance(e, wiki.NotIndexable):
            wiki.logger.exception(f"Errore indicizzando {path}")
        if old_chunks:
            wiki.delete_chunks(path, range(old_chunks))
        wiki.write_status(path, {"state": "error", "chunks": 0, "error": str(e)})
        return
    if old_chunks > len(chunks):
        wiki.delete_chunks(path, range(len(chunks), old_chunks))
    wiki.write_status(path, {"state": "ready", "chunks": len(chunks), "lines": len(text.splitlines()),
                             "size": obj.get("ContentLength", 0), "etag": obj.get("ETag", "").strip('"')})
    wiki.logger.info(f"Indicizzato {path}: {len(chunks)} parti")
