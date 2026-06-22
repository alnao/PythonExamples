from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_shared_llama: Any = None

def get_shared_llama(model_path: str | None) -> Any:
    global _shared_llama
    if not model_path:
        raise ValueError("model_path is required")
    if _shared_llama is None:
        try:
            from llama_cpp import Llama
        except Exception as exc:
            raise RuntimeError("llama_cpp_python is not installed or failed to import") from exc
        logger.info(f"Loading shared Llama model from {model_path}...")
        _shared_llama = Llama(
            model_path=str(model_path),
            embedding=True,
            n_ctx=4096,
            n_gpu_layers=-1
        )
    return _shared_llama
