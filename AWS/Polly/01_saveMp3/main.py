"""
AWS Polly - Save MP3 to S3
Receives a list of items (id, uuid, nome, pathS3, keyS3, testoDaLeggere),
synthesizes each text with AWS Polly and uploads the MP3 to the given S3 bucket/key.

TO RUN:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8001
Then open http://localhost:8001 in a browser.

AWS credentials must be configured (aws configure or env vars / IAM role).
"""

import os
from typing import List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

PROFILE_NAME = os.getenv("AWS_PROFILE", "default")
AWS_REGION   = os.getenv("AWS_REGION", "eu-west-1")

session = boto3.Session(profile_name=PROFILE_NAME, region_name=AWS_REGION)
polly   = session.client("polly")
s3      = session.client("s3")

app = FastAPI(title="AWS Polly – Save MP3 to S3")
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


# ── Models ────────────────────────────────────────────────────────────────────

class TextItem(BaseModel):
    id: str
    uuid: str
    nome: str
    pathS3: str        # S3 bucket name
    keyS3: str         # S3 object key (e.g. "audio/hello.mp3")
    testoDaLeggere: str


class SynthesizeRequest(BaseModel):
    voice_id: str = "Bianca"
    engine: str = "neural"
    items: List[TextItem]


class ItemResult(BaseModel):
    id: str
    uuid: str
    nome: str
    s3_uri: str
    status: str        # "success" | "error"
    message: str


class SynthesizeResponse(BaseModel):
    results: List[ItemResult]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/voices")
def list_voices(language_code: Optional[str] = None):
    """Return available Polly voices, optionally filtered by language code."""
    params: dict = {}
    if language_code:
        params["LanguageCode"] = language_code
    voices: list = []
    while True:
        try:
            response = polly.describe_voices(**params)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        voices.extend(response.get("Voices", []))
        token = response.get("NextToken")
        if not token:
            break
        params["NextToken"] = token
    return {"voices": voices}


@app.post("/synthesize", response_model=SynthesizeResponse)
def synthesize(payload: SynthesizeRequest):
    """
    For each item: synthesize text → MP3 via Polly, then upload to S3.
    Returns per-item status.
    """
    results: List[ItemResult] = []

    for item in payload.items:
        s3_uri = f"s3://{item.pathS3}/{item.keyS3}"
        try:
            # 1. Synthesize with Polly
            polly_response = polly.synthesize_speech(
                Text=item.testoDaLeggere,
                VoiceId=payload.voice_id,
                OutputFormat="mp3",
                Engine=payload.engine,
            )
            audio_data = polly_response["AudioStream"].read()

            # 2. Upload to S3
            s3.put_object(
                Bucket=item.pathS3,
                Key=item.keyS3,
                Body=audio_data,
                ContentType="audio/mpeg",
            )

            results.append(
                ItemResult(
                    id=item.id,
                    uuid=item.uuid,
                    nome=item.nome,
                    s3_uri=s3_uri,
                    status="success",
                    message="MP3 saved to S3 successfully",
                )
            )
        except (BotoCoreError, ClientError) as exc:
            results.append(
                ItemResult(
                    id=item.id,
                    uuid=item.uuid,
                    nome=item.nome,
                    s3_uri=s3_uri,
                    status="error",
                    message=str(exc),
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                ItemResult(
                    id=item.id,
                    uuid=item.uuid,
                    nome=item.nome,
                    s3_uri=s3_uri,
                    status="error",
                    message=f"Unexpected error: {exc}",
                )
            )

    return SynthesizeResponse(results=results)
