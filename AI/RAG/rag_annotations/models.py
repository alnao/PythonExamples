from __future__ import annotations

from typing import List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class AnnotationIn(BaseModel):
    text: str = Field(min_length=1)
    source: Optional[str] = None


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    annotation_id: str
    text: str
    index: int


class ChunkWithEmbedding(Chunk):
    embedding: List[float]


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class SearchHit(BaseModel):
    chunk_id: str
    annotation_id: str
    score: float
    text: str


class SearchResponse(BaseModel):
    results: List[SearchHit]
