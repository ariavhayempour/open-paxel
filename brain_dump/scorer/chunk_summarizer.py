from __future__ import annotations

from brain_dump.redact.transcript import redact_text

CHUNK_SUMMARY_SYSTEM = """You extend a lossless running summary of a developer's AI coding session.

Rules:
- Preserve EVERY fact from the prior accumulated summary — do not drop or compress away earlier details.
- Add only facts grounded in the new chunk.
- Capture: user intents, steering/corrections, files touched, code changes, shell commands,
  tests/lint, errors/fixes, planning, product decisions, tool usage, outcomes, open questions.
- Include short verbatim quotes when they show steering style or frustration.
- Write dense bullet points grouped by theme. No invented details.
- Redact secrets as [REDACTED] if seen."""


def chunk_summary_user_prompt(
    *,
    chunk: str,
    prior_accumulated: str,
    index: int,
    total: int,
) -> str:
    prior = prior_accumulated.strip() or "(empty — first chunk)"
    return f"""Chunk {index} of {total}.

PRIOR ACCUMULATED SUMMARY (keep all of this):
---
{prior}
---

NEW TRANSCRIPT CHUNK:
---
{chunk}
---

Return the COMPLETE updated accumulated summary (prior + new chunk, lossless merge)."""


def dry_run_chunk_summary(chunk: str, index: int, total: int, prior: str) -> str:
    snippet = redact_text(chunk, 600)
    header = f"## Chunk {index}/{total}\n"
    body = f"- Content sample: {snippet}\n"
    if prior.strip():
        return prior.strip() + "\n\n" + header + body
    return header + body
