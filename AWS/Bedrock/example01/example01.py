
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseSettings
from typing import List
import os, uuid, json
import boto3
import chromadb
from chromadb.utils import embedding_functions

# uvicorn app.main:app --host 0.0.0.0 --port 8000

class Settings(BaseSettings):
    AWS_REGION: str = "eu-central-1"
    S3_BUCKET: str = "ragdemo-bucket"
    CHROMA_DIR: str = "./chroma"
    BEDROCK_EMBEDDING_MODEL: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_CHAT_MODEL: str = "meta.llama3-70b-instruct-v1:0"  # adjust to what you enabled
settings = Settings()

app = FastAPI(title="Pocket RAG")

# Chroma (local, sqlite)
os.makedirs(settings.CHROMA_DIR, exist_ok=True)
client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
collection = client.get_or_create_collection(name="docs")

bedrock = boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)

def bedrock_embed(texts: List[str]) -> List[List[float]]:
    body = json.dumps({"inputText": texts})  # Titan v2 supports batch
    resp = bedrock.invoke_model(
        modelId=settings.BEDROCK_EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(resp["body"].read())
    return [item["embedding"] for item in payload["embedding"]]

def bedrock_chat(prompt: str) -> str:
    body = {
        "messages": [{"role":"user","content":[{"type":"text","text":prompt}]}],
        "max_tokens": 512, "temperature": 0.2, "top_p": 0.9
    }
    resp = bedrock.invoke_model(
        modelId=settings.BEDROCK_CHAT_MODEL,
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
    r = collection.query(query_texts=[q], n_results=k)
    ctx = "\n\n".join(r["documents"][0])
    prompt = f"Use the context to answer.\n\n# Context\n{ctx}\n\n# Question\n{q}\n\n# Answer:"
    answer = bedrock_chat(prompt)
    return {"answer": answer, "chunks": r["documents"][0], "ids": r["ids"][0]}

@app.post("/generate")
async def generate(prompt: str):
    return {"answer": bedrock_chat(prompt)}