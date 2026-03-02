from __future__ import annotations

from typing import Iterable, List

from .chunker import split_text
from .config import settings
from .llm.providers import build_provider
from .models import AnnotationIn, Chunk, ChunkWithEmbedding, SearchResponse
from .vector_store.chroma_store import ChromaStore


class Pipeline:
    def __init__(self):
        self._embedder = build_provider()
        self._store = ChromaStore()

    def ingest(self, items: Iterable[AnnotationIn]) -> int:
        chunks: List[Chunk] = []
        for ann in items:
            annotation_id = ann.source or ann.text[:16]
            for idx, piece in enumerate(split_text(ann.text, settings.chunk_size, settings.chunk_overlap)):
                chunks.append(Chunk(annotation_id=annotation_id, text=piece, index=idx))
        embeddings = self._embedder.embed([c.text for c in chunks]) if chunks else []
        with_embeddings: List[ChunkWithEmbedding] = []
        for chunk, emb in zip(chunks, embeddings):
            with_embeddings.append(ChunkWithEmbedding(**chunk.dict(), embedding=emb))
        self._store.add(with_embeddings)
        return len(chunks)

    def search(self, query: str, top_k: int | None = None) -> SearchResponse:
        top = top_k or settings.top_k
        [query_embedding] = self._embedder.embed([query])
        hits = self._store.search(query_embedding, top)
        return SearchResponse(results=hits)

    def search_with_backend(self, query: str, top_k: int | None, backend: str) -> SearchResponse:
        top = top_k or settings.top_k
        embedder = build_provider(backend_override=backend)
        [query_embedding] = embedder.embed([query])
        hits = self._store.search(query_embedding, top)
        return SearchResponse(results=hits)
