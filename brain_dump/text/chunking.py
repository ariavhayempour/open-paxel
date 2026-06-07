from __future__ import annotations

from brain_dump.text.tokens import divide_into_chunks, estimate_tokens

# Longer analysis chunks (estimated tokens).
ANALYSIS_CHUNK_TOKENS = 10_000

# Use chunk summarization when transcript exceeds this size, or unstructured text above floor.
CHUNK_SUMMARIZE_THRESHOLD = 10_000
UNSTRUCTURED_SUMMARIZE_FLOOR = 1200

__all__ = [
    "ANALYSIS_CHUNK_TOKENS",
    "CHUNK_SUMMARIZE_THRESHOLD",
    "UNSTRUCTURED_SUMMARIZE_FLOOR",
    "divide_into_chunks",
    "estimate_tokens",
    "needs_chunk_summarization",
]


def needs_chunk_summarization(
    *,
    total_tokens: int,
    is_structured: bool,
    transcript_tokens: int | None = None,
) -> bool:
    size = transcript_tokens if transcript_tokens is not None else total_tokens
    if not is_structured and size >= UNSTRUCTURED_SUMMARIZE_FLOOR:
        return True
    return size > CHUNK_SUMMARIZE_THRESHOLD
