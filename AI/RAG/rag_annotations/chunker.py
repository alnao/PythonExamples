from __future__ import annotations

from typing import List


def split_text(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    text = text.strip()
    if not text:
        return []

    # Safeguard parameters
    if size <= 0:
        size = 500
    if overlap < 0 or overlap >= size:
        overlap = int(size * 0.1)

    # Order of separators to try
    separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def _recursive_split(segment: str, separator_idx: int) -> List[str]:
        if len(segment) <= size:
            return [segment]

        if separator_idx >= len(separators):
            return [segment[i : i + size] for i in range(0, len(segment), size)]

        sep = separators[separator_idx]
        if sep == "":
            parts = list(segment)
        else:
            parts = segment.split(sep)

        chunks: List[str] = []
        current_chunk = ""

        for part in parts:
            if sep != "" and current_chunk:
                candidate = current_chunk + sep + part
            else:
                candidate = part

            if len(candidate) <= size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(part) > size:
                    sub_chunks = _recursive_split(part, separator_idx + 1)
                    if sub_chunks:
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1]
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # 1. Split without overlap
    raw_chunks = _recursive_split(text, 0)
    if not raw_chunks:
        return []

    # 2. Apply overlap only at top level
    final_chunks = []
    for i, chk in enumerate(raw_chunks):
        if i == 0:
            final_chunks.append(chk)
        else:
            prev_chk = raw_chunks[i - 1]
            overlap_candidate = prev_chk[-overlap:] if len(prev_chk) >= overlap else prev_chk
            first_space = overlap_candidate.find(" ")
            if first_space != -1 and first_space < len(overlap_candidate) - 1:
                overlap_candidate = overlap_candidate[first_space + 1 :]
            
            combined = overlap_candidate
            if not chk.startswith(" ") and not overlap_candidate.endswith(" "):
                if not any(s in overlap_candidate[-1:] or s in chk[:1] for s in ["\n", "\r"]):
                    combined += " "
            combined += chk
            final_chunks.append(combined)

    return final_chunks
