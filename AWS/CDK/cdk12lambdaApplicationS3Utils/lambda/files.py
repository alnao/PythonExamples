"""Lambda sui file del bucket, avviate dalle regole EventBridge.

- decompress: archivio caricato in INPUT/ (zip, tar, tar.gz, tgz) -> file estratti in DEZIPPED/
- convert_to_csv: file Excel in DEZIPPED/ -> primo foglio salvato come CSV in CSV/ (openpyxl, dal layer)
"""

import csv
import io
import mimetypes
import os
import tarfile
import zipfile

from common import client, folder, s3_object, safe_name


def _put(bucket: str, key: str, content: bytes):
    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    client("s3").put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
    print(f"scritto s3://{bucket}/{key} ({len(content)} byte)")


def extract(name: str, data: bytes):
    """Coppie (percorso, contenuto) dei file dell'archivio; un file non archivio viene restituito com'e'."""
    lower = name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
    elif lower.endswith((".tar", ".tar.gz", ".tgz")):
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    yield member.name, archive.extractfile(member).read()
    else:
        yield os.path.basename(name), data


def decompress(event, context):
    bucket, key = s3_object(event)
    data = client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
    written = []
    for path, content in extract(key, data):
        target = folder("DEZIPPED_FOLDER") + safe_name(path)
        _put(bucket, target, content)
        written.append(target)
    return {"archivio": key, "file": written}


def excel_to_csv(data: bytes) -> str:
    import openpyxl  # nel layer delle librerie (build_layer.sh)

    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        for row in workbook.worksheets[0].iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                writer.writerow(["" if cell is None else cell for cell in row])
        return output.getvalue()
    finally:
        workbook.close()


def convert_to_csv(event, context):
    bucket, key = s3_object(event)
    data = client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
    target = folder("CSV_FOLDER") + os.path.splitext(os.path.basename(key))[0] + ".csv"
    _put(bucket, target, excel_to_csv(data).encode("utf-8"))
    return {"excel": key, "csv": target}
