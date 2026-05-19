from io import BytesIO
import os

from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

PROFILE_NAME = os.getenv("AWS_PROFILE", "default")
AUDIO_FORMATS = {
    "mp3": "audio/mpeg",
    "ogg_vorbis": "audio/ogg",
    "pcm": "audio/wave; codecs=1",
}

session = Session(profile_name=PROFILE_NAME)
polly = session.client("polly")

app = FastAPI(title="AWS Polly FastAPI Example")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/voices")
def list_voices() -> JSONResponse:
    params = {}
    voices = []

    while True:
        try:
            response = polly.describe_voices(**params)
        except (BotoCoreError, ClientError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        voices.extend(response.get("Voices", []))
        token = response.get("NextToken")
        if not token:
            break
        params = {"NextToken": token}

    return JSONResponse(voices)


@app.get("/synthesize")
def synthesize(
    text: str = Query(min_length=1, max_length=1000),
    voice_id: str = Query(alias="voiceId", min_length=1),
    output_format: str = Query(alias="outputFormat", default="mp3"),
):
    if output_format not in AUDIO_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported output format")

    try:
        response = polly.synthesize_speech(
            Text=text,
            VoiceId=voice_id,
            OutputFormat=output_format,
            Engine="neural",
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    audio_stream = response.get("AudioStream")
    if not audio_stream:
        raise HTTPException(status_code=500, detail="Empty audio stream")

    payload = audio_stream.read()
    return StreamingResponse(BytesIO(payload), media_type=AUDIO_FORMATS[output_format])
