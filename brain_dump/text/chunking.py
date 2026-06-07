from __future__ import annotations

from brain_dump.text.tokens import divide_into_chunks, estimate_tokens

# Max redacted transcript chars sent to the scoring model in one call.
MAX_SESSION_TRANSCRIPT_CHARS = 500_000

__all__ = [
    "MAX_SESSION_TRANSCRIPT_CHARS",
    "divide_into_chunks",
    "estimate_tokens",
]
