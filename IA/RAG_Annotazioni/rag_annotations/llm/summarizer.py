from __future__ import annotations

from typing import Tuple

from ..config import settings


class BaseSummarizer:
    def summarize(self, text: str) -> Tuple[str, str]:
        raise NotImplementedError


class LocalLlamaSummarizer(BaseSummarizer):
    def __init__(self, model_path: str | None):
        try:
            from llama_cpp import Llama
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("llama_cpp_python is not installed or failed to import") from exc
        if not model_path:
            raise ValueError("model_path is required for local summarizer")
        # Reuse the model for generation
        self._llama = Llama(model_path=str(model_path), n_ctx=4096, n_gpu_layers=-1, embedding=False)

    def summarize(self, text: str) -> Tuple[str, str]:  # pragma: no cover - integration
        prompt = (
            "You are a concise assistant. Given the following chunk of text, write a very short abstract (max 3 sentences) "
            "in the original language of the chunk. Then provide an Italian translation of that abstract prefixed with 'IT:'.\n\n"
            f"Chunk:\n{text}\n\nAbstract:"
        )
        resp = self._llama.create_completion(prompt=prompt, max_tokens=256, temperature=0.2)
        full = resp["choices"][0]["text"].strip()
        # Split abstract and italian translation if present
        abstract_en = full
        abstract_it = ""
        if "IT:" in full:
            parts = full.split("IT:", 1)
            abstract_en = parts[0].strip()
            abstract_it = parts[1].strip()
        return abstract_en, abstract_it


class OpenAISummarizer(BaseSummarizer):
    def __init__(self, api_key: str | None, model: str):
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package missing") from exc
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when llm_backend=openai")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def summarize(self, text: str) -> Tuple[str, str]:  # pragma: no cover - integration
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a concise assistant. Given a chunk of text, produce a very short abstract (max 3 sentences) "
                    "in the original language. Then provide an Italian translation prefixed with 'IT:'."
                ),
            },
            {"role": "user", "content": text},
        ]
        resp = self._client.chat.completions.create(model=self._model, messages=messages, max_tokens=256, temperature=0.2)
        content = resp.choices[0].message.content.strip()
        abstract_en = content
        abstract_it = ""
        if "IT:" in content:
            parts = content.split("IT:", 1)
            abstract_en = parts[0].strip()
            abstract_it = parts[1].strip()
        return abstract_en, abstract_it


def build_summarizer(backend_override: str | None = None) -> BaseSummarizer:
    backend = (backend_override or settings.llm_backend).lower()
    if backend == "local":
        return LocalLlamaSummarizer(model_path=settings.model_path)
    if backend == "openai":
        return OpenAISummarizer(api_key=settings.openai_api_key, model=settings.openai_model)
    if backend == "hybrid":
        # Prefer local; fallback handled by caller if desired
        return LocalLlamaSummarizer(model_path=settings.model_path)
    raise ValueError(f"Unknown summarizer backend: {backend}")
