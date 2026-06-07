from __future__ import annotations

import re
from dataclasses import dataclass

from brain_dump.parser.patterns import (
    CAPS_FRUSTRATION,
    CODE_FENCE,
    QUESTION_PATTERN,
    REDIRECT_PATTERN,
    TEST_LINT_PATTERN,
    THANK_PATTERN,
)
from brain_dump.text.tokens import estimate_tokens

FILE_PATH_PATTERN = re.compile(
    r"(?:^|\s)(?:[\w./\\-]+\.(?:py|ts|tsx|js|jsx|go|rs|md|json|yaml|yml|toml))(?:\s|$|:)",
    re.I | re.M,
)
PLAN_PATTERN = re.compile(
    r"\b(plan|roadmap|architecture|design doc|step \d|phase \d|before we (code|implement))\b",
    re.I,
)
ERROR_PATTERN = re.compile(r"\b(error|failed|exception|traceback|bug|fix)\b", re.I)


@dataclass
class DocumentStats:
    total_tokens: int
    total_chars: int
    paragraph_count: int
    code_block_count: int
    code_tokens: int
    bash_block_count: int
    diff_lines_added: int
    diff_lines_removed: int
    file_path_mentions: int
    redirect_hits: int
    question_hits: int
    thank_you_hits: int
    caps_frustration_hits: int
    test_lint_hits: int
    plan_hits: int
    error_hits: int
    estimated_turns: int


def scan_document(text: str) -> DocumentStats:
    """Token-aware pass over the full document for heuristic signals."""
    stripped = text.strip()
    total_tokens = estimate_tokens(stripped)
    paragraphs = [p for p in re.split(r"\n{2,}", stripped) if p.strip()]

    code_blocks = list(CODE_FENCE.finditer(stripped))
    code_block_count = len(code_blocks)
    code_tokens = sum(estimate_tokens(m.group(1)) for m in code_blocks)
    bash_block_count = sum(
        1 for m in code_blocks if m.group(0).lower().startswith("```bash")
    )

    diff_lines = [ln for ln in stripped.splitlines() if ln.startswith(("+", "-"))]
    lines_added = sum(
        1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++")
    )
    lines_removed = sum(
        1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---")
    )

    # Estimate conversational turns from size when labels are missing
    avg_turn_tokens = 350
    estimated_turns = max(
        len(paragraphs) // 2,
        max(1, total_tokens // avg_turn_tokens),
    )

    return DocumentStats(
        total_tokens=total_tokens,
        total_chars=len(stripped),
        paragraph_count=len(paragraphs),
        code_block_count=code_block_count,
        code_tokens=code_tokens,
        bash_block_count=bash_block_count,
        diff_lines_added=lines_added,
        diff_lines_removed=lines_removed,
        file_path_mentions=len(FILE_PATH_PATTERN.findall(stripped)),
        redirect_hits=len(REDIRECT_PATTERN.findall(stripped)),
        question_hits=len(QUESTION_PATTERN.findall(stripped)),
        thank_you_hits=len(THANK_PATTERN.findall(stripped)),
        caps_frustration_hits=len(CAPS_FRUSTRATION.findall(stripped)),
        test_lint_hits=len(TEST_LINT_PATTERN.findall(stripped)),
        plan_hits=len(PLAN_PATTERN.findall(stripped)),
        error_hits=len(ERROR_PATTERN.findall(stripped)),
        estimated_turns=estimated_turns,
    )
