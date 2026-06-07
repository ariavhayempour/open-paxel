from __future__ import annotations

from pathlib import Path

from brain_dump.models.domain import SessionFacts
from brain_dump.parser.claude_jsonl import ClaudeCodeJsonlParser
from brain_dump.parser.patterns import SUPPORTED_TRANSCRIPT_SUFFIXES
from brain_dump.parser.text_session import TextSessionParser


def is_supported_transcript(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_TRANSCRIPT_SUFFIXES


class AutoTranscriptParser:
    """Pick the right parser based on file extension."""

    def __init__(self) -> None:
        self._jsonl = ClaudeCodeJsonlParser()
        self._text = TextSessionParser()

    def parse(self, path: Path) -> SessionFacts:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".jsonl":
            return self._jsonl.parse(path)
        if suffix in (".md", ".markdown", ".txt"):
            return self._text.parse(path)
        raise ValueError(
            f"Unsupported transcript format '{suffix}'. "
            f"Use one of: {', '.join(SUPPORTED_TRANSCRIPT_SUFFIXES)}"
        )
