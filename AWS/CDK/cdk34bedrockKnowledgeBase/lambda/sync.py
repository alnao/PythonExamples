"""
Lambda di sincronizzazione: riceve dalla coda SQS gli eventi S3 (file aggiunti o cancellati in uploads/)
e avvia una sincronizzazione della Knowledge Base per tutto il gruppo di messaggi.

La sincronizzazione e' incrementale (Bedrock indicizza solo i file nuovi o cambiati e toglie quelli
cancellati), quindi una basta per molti eventi. Se ne e' gia' in corso una, la Lambda fallisce: i
messaggi tornano visibili dopo il visibility timeout della coda e si riprova (fino a 30 volte).
"""

import json
from urllib.parse import unquote_plus

import kb


class SyncBusy(Exception):
    """Sincronizzazione gia' in corso: i messaggi restano in coda."""


def changed_keys(event) -> list:
    keys = []
    for message in event.get("Records", []):
        body = json.loads(message.get("body") or "{}")
        # S3 manda un s3:TestEvent quando configura la notifica: nessun file cambiato
        for record in body.get("Records", []):
            keys.append(unquote_plus(record["s3"]["object"]["key"]))
    return keys


def handler(event, context):
    keys = changed_keys(event)
    if not keys:
        kb.logger.info("Nessun file cambiato nei messaggi")
        return {"started": None}
    job = kb.start_sync(f"{len(keys)} file cambiati, es. {keys[0]}")
    if job is None:
        raise SyncBusy(f"sincronizzazione gia' in corso: {len(keys)} file restano in coda")
    kb.logger.info(f"Sincronizzazione {job['id']} avviata per {len(keys)} file")
    return {"started": job["id"], "files": len(keys)}
