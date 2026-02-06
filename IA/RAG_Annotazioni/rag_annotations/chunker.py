from __future__ import annotations

from typing import List


def split_text(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks
