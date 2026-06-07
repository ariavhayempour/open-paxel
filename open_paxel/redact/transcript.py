from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),
]


def redact_text(text: str, max_len: int = 800) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def read_full_transcript(facts) -> str:
    parts = [m.text for m in facts.user_messages]
    if facts.assistant_text_chars:
        parts.append("[assistant output omitted from structured export]")
    path = facts.transcript_path
    if path and not facts.is_structured:
        try:
            from pathlib import Path

            raw = Path(path).read_text(encoding="utf-8")
            if raw.strip():
                return raw
        except OSError:
            pass
    if path and facts.is_structured:
        try:
            from pathlib import Path

            raw = Path(path).read_text(encoding="utf-8")
            if estimate_tokens_from_raw(raw) > estimate_tokens_from_parts(parts):
                return raw
        except OSError:
            pass
    return "\n\n".join(parts)


def estimate_tokens_from_raw(text: str) -> int:
    from open_paxel.text.tokens import estimate_tokens

    return estimate_tokens(text)


def estimate_tokens_from_parts(parts: list[str]) -> int:
    from open_paxel.text.tokens import estimate_tokens

    return estimate_tokens("\n\n".join(parts))
