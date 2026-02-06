from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException, Query

from rag_annotations.models import AnnotationIn, SearchRequest, SearchResponse
from rag_annotations.pipeline import Pipeline

app = FastAPI(title="RAG Annotazioni", version="0.1.0")
pipeline = Pipeline()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/annotations")
def ingest_annotations(payload: List[AnnotationIn]) -> dict:
    if not payload:
        raise HTTPException(status_code=400, detail="No annotations provided")
    count = pipeline.ingest(payload)
    return {"ingested_chunks": count}


@app.get("/search", response_model=SearchResponse)
def search(query: str = Query(..., min_length=1), top_k: int = Query(5, ge=1, le=50)) -> SearchResponse:
    return pipeline.search(query=query, top_k=top_k)


@app.post("/search", response_model=SearchResponse)
def search_post(request: SearchRequest) -> SearchResponse:
    return pipeline.search(query=request.query, top_k=request.top_k)
