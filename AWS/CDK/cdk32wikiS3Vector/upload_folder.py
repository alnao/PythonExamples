#!/usr/bin/env python3
"""
Carica nella wiki tutti i file di testo di una cartella, sincronizzandola con il bucket dei file.

- carica solo i file nuovi o modificati (MD5 del file locale confrontato con l'ETag su S3)
- con --delete cancella dal bucket i file che non ci sono piu' nella cartella
- ogni file caricato o cancellato fa partire da solo l'indicizzazione (evento S3 -> Lambda Ingest)
- salta cartelle nascoste e di servizio (.git, node_modules, venv, cdk.out, ...), i file oltre
  MAX_FILE_KB, quelli indicati con --exclude e quelli che sembrano contenere credenziali

Esempi:
    python upload_folder.py ../../..                          # tutto il repository PythonExamples
    python upload_folder.py ../../../AWS --prefix AWS          # solo AWS/, salvata come AWS/...
    python upload_folder.py ../../.. --delete --dry-run        # mostra cosa farebbe, senza toccare nulla
    python upload_folder.py ../../.. --exclude "AI/*" --exclude "*.csv"
    python upload_folder.py ../../.. --yes                    # senza chiedere conferma del costo stimato
"""

import argparse
import fnmatch
import hashlib
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lambda"))
from wiki import MAX_FILE_KB, is_supported  # noqa: E402  (stesse regole della Lambda Ingest)

STACK_NAME = "Cdk32WikiS3VectorStack"
# stima del costo degli embedding: Titan Text Embeddings V2 in eu-central-1, IVA esclusa (verificato sul
# conto di ottobre 2026: 1,35 milioni di token addebitati 0,27 $); oltre COST_CONFIRM_USD si chiede conferma
TITAN_USD_PER_MTOKEN = 0.20
CHARS_PER_TOKEN = 4         # media indicativa per testi italiani, inglesi e codice
CHUNK_OVERHEAD = 1.1        # 3 righe ripetute tra le parti e il percorso del file nel testo
COST_CONFIRM_USD = 0.01
SKIP_DIRS = {"node_modules", "venv", "__pycache__", "cdk.out", "layer", "cache", "dist", "build"}
# contenuti che fanno pensare a credenziali: il file non viene caricato
SECRET_PATTERNS = [re.compile(p) for p in (
    r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",                 # access key id AWS
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",          # chiave privata
    # secret access key AWS: 40 caratteri base64 isolati, con maiuscole, minuscole e cifre
    # (gli hash esadecimali come quelli di git sono tutti minuscoli e non vengono presi)
    r"(?<![A-Za-z0-9/+=])(?=[A-Za-z0-9/+]*[A-Z])(?=[A-Za-z0-9/+]*[a-z])(?=[A-Za-z0-9/+]*[0-9])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])",
)]


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def local_files(folder: str, prefix: str, excludes):
    """File da caricare {percorso nella wiki: (file locale, md5)} e file saltati [(file, motivo)]."""
    found, skipped = {}, []
    for root, dirs, names in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(names):
            full = os.path.join(root, name)
            relative = os.path.relpath(full, folder).replace(os.sep, "/")
            path = f"{prefix.strip('/')}/{relative}" if prefix.strip("/") else relative
            if name.startswith(".") and not name.endswith(".example"):
                continue
            if not is_supported(path):
                continue
            if any(fnmatch.fnmatch(path, pattern) for pattern in excludes):
                skipped.append((path, "escluso con --exclude"))
                continue
            if os.path.getsize(full) > MAX_FILE_KB * 1024:
                skipped.append((path, f"oltre {MAX_FILE_KB} KB"))
                continue
            data = open(full, "rb").read()
            if any(p.search(data.decode("utf-8", errors="ignore")) for p in SECRET_PATTERNS):
                skipped.append((path, "sembra contenere credenziali"))
                continue
            found[path] = (full, md5(data))
    return found, skipped


def remote_files(s3, bucket: str, prefix: str):
    """File gia' nel bucket {percorso nella wiki: ETag} (solo sotto il prefisso scelto)."""
    found = {}
    start = "files/" + (prefix.strip("/") + "/" if prefix.strip("/") else "")
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=start):
        for obj in page.get("Contents", []):
            found[obj["Key"][len("files/"):]] = obj["ETag"].strip('"')
    return found


def plan(local: dict, remote: dict, delete: bool):
    """Cosa fare: (da caricare, da cancellare, invariati)."""
    upload = sorted(p for p, (_, digest) in local.items() if remote.get(p) != digest)
    remove = sorted(p for p in remote if p not in local) if delete else []
    unchanged = len(local) - len(upload)
    return upload, remove, unchanged


def embedding_cost(total_bytes: int):
    """(token, dollari) stimati per indicizzare file di testo per total_bytes byte."""
    tokens = int(total_bytes * CHUNK_OVERHEAD / CHARS_PER_TOKEN)
    return tokens, tokens * TITAN_USD_PER_MTOKEN / 1_000_000


def bucket_from_stack(session, stack: str) -> str:
    outputs = session.client("cloudformation").describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])
    for output in outputs:
        if output["OutputKey"] == "FilesBucket":
            return output["OutputValue"]
    sys.exit(f"Output FilesBucket non trovato nello stack {stack}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", help="cartella da caricare")
    parser.add_argument("--prefix", default="", help="percorso nella wiki sotto cui mettere i file (es. AWS)")
    parser.add_argument("--delete", action="store_true", help="cancella dal bucket i file spariti dalla cartella")
    parser.add_argument("--dry-run", action="store_true", help="mostra cosa farebbe senza caricare ne' cancellare")
    parser.add_argument("--yes", action="store_true", help="carica senza chiedere conferma del costo stimato")
    parser.add_argument("--exclude", action="append", default=[], help="percorsi da saltare (es. \"AI/*\"), ripetibile")
    parser.add_argument("--bucket", help="bucket dei file (default: output FilesBucket dello stack)")
    parser.add_argument("--stack", default=STACK_NAME)
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--profile")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        sys.exit(f"Cartella non trovata: {args.folder}")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    bucket = args.bucket or bucket_from_stack(session, args.stack)
    s3 = session.client("s3")

    local, skipped = local_files(args.folder, args.prefix, args.exclude)
    remote = remote_files(s3, bucket, args.prefix)
    upload, remove, unchanged = plan(local, remote, args.delete)

    for path, reason in skipped:
        print(f"  saltato   {path} ({reason})")
    for path in upload:
        print(f"  {'nuovo    ' if path not in remote else 'modificato'} {path}")
    for path in remove:
        print(f"  da togliere {path}")
    print(f"Bucket {bucket}: {len(upload)} da caricare, {len(remove)} da cancellare, {unchanged} invariati, {len(skipped)} saltati")
    tokens, usd = embedding_cost(sum(os.path.getsize(local[p][0]) for p in upload))
    if upload:
        print(f"Costo stimato degli embedding: circa {usd:.3f} $ (~{tokens:,} token Titan, stima indicativa IVA esclusa)")
    if args.dry_run or not (upload or remove):
        return
    if usd >= COST_CONFIRM_USD and not args.yes:
        if input("Potrebbe avere costi indesiderati. Procediamo? [s/N] ").strip().lower() not in ("s", "si", "sì", "y", "yes"):
            sys.exit("Annullato: nessun file caricato")

    def put(path):
        full, _ = local[path]
        s3.put_object(Bucket=bucket, Key=f"files/{path}", Body=open(full, "rb").read(),
                      ContentType="text/plain; charset=utf-8")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(put, upload))
    for start in range(0, len(remove), 1000):
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": f"files/{p}"} for p in remove[start:start + 1000]]})
    print("Fatto: l'indicizzazione parte da sola, lo stato dei file e' nella pagina 'File' della wiki")


if __name__ == "__main__":
    main()
