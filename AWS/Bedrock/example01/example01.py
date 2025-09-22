
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
#from pydantic import BaseSettings
from pydantic_settings import BaseSettings
from typing import List
import os, uuid, json
import boto3
import chromadb
from chromadb.utils import embedding_functions

# Recupera dinamicamente regione e account ID
session = boto3.session.Session()
aws_region = session.region_name or "eu-central-1"
account_id = session.client("sts").get_caller_identity()["Account"]

class Settings(BaseSettings):
    AWS_REGION: str = aws_region
    S3_BUCKET: str = "ragdemo-alnao-bucket"
    CHROMA_DIR: str = "./chroma"
    BEDROCK_EMBEDDING_MODEL: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_CHAT_MODEL: str = "meta.llama3-2-3b-instruct-v1:0"  # adjust to what you enabled
    INFERENCE_PROFILE_ARN: str = f"arn:aws:bedrock:{aws_region}:{account_id}:inference-profile/eu.meta.llama3-2-3b-instruct-v1:0"
    USE_LOCAL_EMBEDDINGS: bool = True  # Fallback to local embeddings if Bedrock is not accessible

settings = Settings()

app = FastAPI(title="Pocket RAG")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chroma (local, sqlite)
os.makedirs(settings.CHROMA_DIR, exist_ok=True)
client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
# Use a different collection name for Bedrock embeddings to avoid dimension mismatch
collection = client.get_or_create_collection(name="docs-bedrock")

bedrock = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)


def bedrock_embed_batch(texts: List[str]) -> List[List[float]]:
    # Use Bedrock (original code)
    body = json.dumps({"inputText": texts})  # Titan v2 supports batch
    resp = bedrock.invoke_model(
        modelId=settings.BEDROCK_EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    return [item["embedding"] for item in payload["embedding"]]


def bedrock_embed(texts: List[str]) -> List[List[float]]:
    # Use Bedrock - process texts individually as Titan v2 expects single strings
    embeddings = []
    for text in texts:
        body = json.dumps({"inputText": text})
        resp = bedrock.invoke_model(
            modelId=settings.BEDROCK_EMBEDDING_MODEL,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(resp["body"].read())
        embeddings.append(payload["embedding"])
    return embeddings

def bedrock_chat(prompt: str) -> str:
    # Different body format for Llama 3.2 3B Instruct
    body = {
        "prompt": prompt,
        "temperature": 0.2,
        "top_p": 0.9
    }
    # Use inference profile ARN as modelId if available, otherwise use regular model ID
    model_id = settings.INFERENCE_PROFILE_ARN if settings.INFERENCE_PROFILE_ARN else settings.BEDROCK_CHAT_MODEL
    
    resp = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    out = json.loads(resp["body"].read())
    # meta llama uses "output" or "content" depending on version; normalize:
    if "output" in out:  # some providers
        return out["output"]["message"]["content"][0]["text"]
    if "content" in out:
        return out["content"][0]["text"]
    return str(out)

@app.get("/health") 
def health(): return {"ok": True}

@app.post("/ingest")
async def ingest(file: UploadFile = File(...), doc_id: str = Form(default=None)):
    text = (await file.read()).decode("utf-8", errors="ignore")
    # naive splitter:
    chunks = [text[i:i+1200] for i in range(0, len(text), 1200)]
    embeds = bedrock_embed(chunks)
    ids = [f"{doc_id or uuid.uuid4()}_{i}" for i in range(len(chunks))]
    collection.add(ids=ids, documents=chunks, embeddings=embeds, metadatas=[{"name":file.filename}] * len(chunks))
    # store raw in S3
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(Bucket=settings.S3_BUCKET, Key=f"uploads/{file.filename}", Body=text.encode())
    return {"added": len(chunks)}

@app.post("/query")
async def query(q: str, k: int = 4):
    # Use Bedrock to embed the query
    query_embedding = bedrock_embed([q])[0]
    r = collection.query(query_embeddings=[query_embedding], n_results=k)
    ctx = "\n\n".join(r["documents"][0])
    prompt = f"Use the context to answer.\n\n# Context\n{ctx}\n\n# Question\n{q}\n\n# Answer:"
    answer = bedrock_chat(prompt)
    return {"answer": answer, "chunks": r["documents"][0], "ids": r["ids"][0]}

@app.post("/generate")
async def generate(prompt: str):
    return {"answer": bedrock_chat(prompt)}