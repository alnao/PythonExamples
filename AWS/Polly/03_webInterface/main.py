"""
AWS Polly - 03_webInterface
Interfaccia web completa per sintetizzare testo con Polly e salvare MP3 su S3.
Supporta: singolo elemento, lista, JSON diretto, visualizzazione MP3 generati.
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, Response, jsonify, render_template, request, send_file

PROFILE_NAME = os.getenv("AWS_PROFILE", "default")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

session = boto3.Session(profile_name=PROFILE_NAME, region_name=AWS_REGION)
polly = session.client("polly")
s3 = session.client("s3")

app = Flask(__name__, template_folder="templates")


def _json_error(status_code: int, message: str) -> tuple[Response, int]:
    return jsonify({"error": message}), status_code


def _validate_payload(payload: Any) -> tuple[dict[str, Any] | None, Response | None, int | None]:
    if not isinstance(payload, dict):
        response, code = _json_error(400, "JSON body non valido")
        return None, response, code

    voice_id = payload.get("voice_id", "Bianca")
    engine = payload.get("engine", "neural")
    items = payload.get("items")

    if not isinstance(voice_id, str) or not voice_id.strip():
        response, code = _json_error(400, "voice_id deve essere una stringa non vuota")
        return None, response, code
    if not isinstance(engine, str) or not engine.strip():
        response, code = _json_error(400, "engine deve essere una stringa non vuota")
        return None, response, code
    if not isinstance(items, list) or not items:
        response, code = _json_error(400, "items deve essere una lista non vuota")
        return None, response, code

    required_keys = {"id", "uuid", "nome", "pathS3", "keyS3", "testoDaLeggere"}
    normalized_items: list[dict[str, str]] = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            response, code = _json_error(400, f"item #{index} deve essere un oggetto")
            return None, response, code
        missing = sorted(required_keys - item.keys())
        if missing:
            response, code = _json_error(400, f"item #{index} manca campi: {', '.join(missing)}")
            return None, response, code
        normalized: dict[str, str] = {}
        for key in required_keys:
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                response, code = _json_error(400, f"item #{index} campo '{key}' non valido")
                return None, response, code
            normalized[key] = value.strip()
        normalized_items.append(normalized)

    return {
        "voice_id": voice_id.strip(),
        "engine": engine.strip(),
        "items": normalized_items,
    }, None, None


def _upload_execution_log(payload: dict[str, Any], results: list[dict[str, str]]) -> list[dict[str, str]]:
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        f"execution_timestamp: {timestamp}",
        f"voice_id: {payload['voice_id']}",
        f"engine: {payload['engine']}",
        f"total_items: {len(payload['items'])}",
        "",
        "=== INPUT ITEMS ===",
    ]
    for item in payload["items"]:
        lines.append(json.dumps(item, ensure_ascii=False))
    lines.extend(["", "=== RESULTS ==="])
    for result in results:
        lines.append(json.dumps(result, ensure_ascii=False))

    log_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    upload_results: list[dict[str, str]] = []
    uploaded_buckets: set[str] = set()

    for item in payload["items"]:
        bucket = item["pathS3"]
        if bucket in uploaded_buckets:
            continue
        try:
            s3.put_object(
                Bucket=bucket,
                Key="execution.log",
                Body=io.BytesIO(log_bytes),
                ContentType="text/plain; charset=utf-8",
            )
            upload_results.append({"bucket": bucket, "key": "execution.log", "status": "success"})
            uploaded_buckets.add(bucket)
        except (BotoCoreError, ClientError) as exc:
            upload_results.append(
                {"bucket": bucket, "key": "execution.log", "status": "error", "message": str(exc)}
            )
    return upload_results


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/voices")
def list_voices() -> tuple[Response, int] | Response:
    language_code = request.args.get("language_code", "").strip()
    params: dict[str, str] = {}
    if language_code:
        params["LanguageCode"] = language_code
    voices: list[dict[str, Any]] = []
    try:
        while True:
            resp = polly.describe_voices(**params)
            voices.extend(resp.get("Voices", []))
            token = resp.get("NextToken")
            if not token:
                break
            params["NextToken"] = token
    except (BotoCoreError, ClientError) as exc:
        return _json_error(500, f"Errore AWS Polly: {exc}")
    return jsonify({"voices": voices})


@app.post("/api/synthesize")
def synthesize() -> tuple[Response, int] | Response:
    payload = request.get_json(silent=True)
    validated, error_response, error_code = _validate_payload(payload)
    if error_response is not None and error_code is not None:
        return error_response, error_code
    assert validated is not None

    results: list[dict[str, str]] = []
    for item in validated["items"]:
        bucket = item["pathS3"]
        key = item["keyS3"]
        s3_uri = f"s3://{bucket}/{key}"
        try:
            polly_response = polly.synthesize_speech(
                Text=item["testoDaLeggere"],
                VoiceId=validated["voice_id"],
                OutputFormat="mp3",
                Engine=validated["engine"],
            )
            audio_data = polly_response["AudioStream"].read()
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=audio_data,
                ContentType="audio/mpeg",
            )
            results.append({
                "id": item["id"],
                "uuid": item["uuid"],
                "nome": item["nome"],
                "bucket": bucket,
                "key": key,
                "s3_uri": s3_uri,
                "status": "success",
                "message": "MP3 salvato su S3",
            })
        except (BotoCoreError, ClientError) as exc:
            results.append({
                "id": item["id"],
                "uuid": item["uuid"],
                "nome": item["nome"],
                "bucket": bucket,
                "key": key,
                "s3_uri": s3_uri,
                "status": "error",
                "message": str(exc),
            })

    log_uploads = _upload_execution_log(validated, results)
    return jsonify({"results": results, "log_uploads": log_uploads})


@app.get("/api/list-mp3")
def list_mp3() -> tuple[Response, int] | Response:
    bucket = request.args.get("bucket", "").strip()
    prefix = request.args.get("prefix", "").strip()
    if not bucket:
        return _json_error(400, "Parametro bucket obbligatorio")

    objects: list[dict[str, Any]] = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        params: dict[str, Any] = {"Bucket": bucket}
        if prefix:
            params["Prefix"] = prefix
        for page in paginator.paginate(**params):
            for obj in page.get("Contents", []):
                key: str = obj.get("Key", "")
                if key.lower().endswith(".mp3"):
                    objects.append({
                        "key": key,
                        "size": obj.get("Size", 0),
                        "last_modified": obj.get("LastModified", "").isoformat()
                        if hasattr(obj.get("LastModified", ""), "isoformat")
                        else str(obj.get("LastModified", "")),
                        "s3_uri": f"s3://{bucket}/{key}",
                    })
    except (BotoCoreError, ClientError) as exc:
        return _json_error(500, f"Errore listaggio S3: {exc}")

    objects.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
    return jsonify({"bucket": bucket, "count": len(objects), "objects": objects})


@app.get("/api/download-mp3")
def download_mp3() -> tuple[Response, int] | Response:
    bucket = request.args.get("bucket", "").strip()
    key = request.args.get("key", "").strip()
    if not bucket or not key:
        return _json_error(400, "Parametri bucket e key obbligatori")
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        file_bytes = resp["Body"].read()
    except (BotoCoreError, ClientError) as exc:
        return _json_error(500, f"Errore download MP3: {exc}")

    filename = key.split("/")[-1] or "audio.mp3"
    return send_file(
        io.BytesIO(file_bytes),
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name=filename,
    )


@app.get("/api/health")
def health() -> Response:
    return jsonify({"status": "ok", "service": "03_webInterface"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003, debug=True)
