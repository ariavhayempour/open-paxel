from __future__ import annotations

import re

REDIRECT_PATTERN = re.compile(
    r"\b(no|don't|dont|stop|wrong|instead|not that|wait|actually)\b", re.I
)
QUESTION_PATTERN = re.compile(r"\?|^(how|why|what|explain)\b", re.I)
THANK_PATTERN = re.compile(r"\b(thanks|thank you|please)\b", re.I)
CAPS_FRUSTRATION = re.compile(r"[A-Z]{4,}.*(?:DON'T|STOP|NOT|TOUCH|SAID)")
TEST_LINT_PATTERN = re.compile(r"\b(pytest|npm test|npm run lint|ruff|mypy|jest)\b", re.I)

SUPPORTED_TRANSCRIPT_SUFFIXES = (".jsonl", ".md", ".markdown", ".txt")

TURN_HEADER = re.compile(
    r"^#{1,4}\s*(?:\*\*)?(User|Human|You|Assistant|AI|Claude|Model|System)(?:\*\*)?\s*:?\s*$",
    re.I | re.M,
)
TURN_INLINE = re.compile(
    r"^(?:\*\*)?(User|Human|You|Assistant|AI|Claude|Model|System)(?:\*\*)?\s*:\s*",
    re.I | re.M,
)
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
H1_TITLE = re.compile(r"^#\s+(.+)$", re.M)
CODE_FENCE = re.compile(r"```[\w-]*\n(.*?)```", re.S)
