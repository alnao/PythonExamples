from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import chromadb
from chromadb import PersistentClient

from ..config import settings
from ..models import ChunkWithEmbedding, SearchHit


class ChromaStore:
    def __init__(self, path: Path | str | None = None, collection_name: str | None = None):
        store_path = Path(path or settings.chroma_path)
        store_path.mkdir(parents=True, exist_ok=True)
        self._client: PersistentClient = chromadb.PersistentClient(path=str(store_path))
        self._collection = self._client.get_or_create_collection(name=collection_name or settings.collection_name)

    def add(self, items: Iterable[ChunkWithEmbedding]) -> None:
        ids: List[str] = []
        docs: List[str] = []
        metas: List[dict] = []
        embeddings: List[List[float]] = []
        for item in items:
            ids.append(item.id)
            docs.append(item.text)
            metas.append({"annotation_id": item.annotation_id, "chunk_index": item.index})
            embeddings.append(item.embedding)
        if ids:
            self._collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    def search(self, embedding: List[float], top_k: int) -> List[SearchHit]:
        result = self._collection.query(query_embeddings=[embedding], n_results=top_k)
        hits: List[SearchHit] = []
        for idx, chunk_id in enumerate(result.get("ids", [[]])[0]):
            metadata = result.get("metadatas", [[]])[0][idx]
            text = result.get("documents", [[]])[0][idx]
            distance = result.get("distances", [[]])[0][idx]
            hits.append(
                SearchHit(
                    chunk_id=chunk_id,
                    annotation_id=str(metadata.get("annotation_id", "")),
                    score=float(distance),
                    text=text,
                )
            )
        return hits
