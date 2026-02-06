from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        raise NotImplementedError


class LocalLlamaProvider(EmbeddingProvider):
    def __init__(self, model_path: str | None):
        try:
            from llama_cpp import Llama
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("llama_cpp_python is not installed or failed to import") from exc
        if not model_path:
            raise ValueError("model_path is required for local backend")
        self._llama = Llama(model_path=str(model_path), embedding=True, n_ctx=2048)

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        # llama_cpp embed returns a list of floats in newer versions, but some builds
        # return a list of per-token vectors. Normalize to a single vector per text.
        def _to_vector(raw) -> List[float]:
            # Handle dict payloads if present
            if isinstance(raw, dict) and "data" in raw:
                raw = raw["data"][0]["embedding"]
            if not raw:
                return []
            first = raw[0]
            if isinstance(first, (int, float)):
                return [float(v) for v in raw]
            if isinstance(first, (list, tuple)):
                dim = len(first)
                acc = [0.0] * dim
                count = 0
                for row in raw:
                    if len(row) != dim:
                        continue
                    count += 1
                    for i, v in enumerate(row):
                        acc[i] += float(v)
                return [v / count for v in acc] if count else []
            raise ValueError("Unsupported embedding format from llama_cpp")

        return [_to_vector(self._llama.embed(t)) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None, model: str):
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package missing") from exc
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when llm_backend=openai")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            resp = self._client.embeddings.create(model=self._model, input=text)
            vectors.append(resp.data[0].embedding)
        return vectors


class FallbackEmbeddingProvider(EmbeddingProvider):
    def __init__(self, primary: EmbeddingProvider, backup: EmbeddingProvider):
        self.primary = primary
        self.backup = backup

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        try:
            return self.primary.embed(texts)
        except Exception:
            return self.backup.embed(texts)


def build_provider(backend_override: str | None = None) -> EmbeddingProvider:
    backend = (backend_override or settings.llm_backend).lower()
    if backend == "local":
        return LocalLlamaProvider(model_path=settings.model_path)
    if backend == "openai":
        return OpenAIEmbeddingProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    if backend == "hybrid":
        primary = LocalLlamaProvider(model_path=settings.model_path)
        backup = OpenAIEmbeddingProvider(api_key=settings.openai_api_key, model=settings.openai_model)
        return FallbackEmbeddingProvider(primary, backup)
    raise ValueError(f"Unknown llm_backend: {backend}")
