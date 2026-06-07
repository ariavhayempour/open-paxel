from __future__ import annotations

from brain_dump.models.domain import RedactedExcerpt
from brain_dump.parser.patterns import REDIRECT_PATTERN
from brain_dump.redact.transcript import read_full_transcript, redact_text
from brain_dump.text.chunking import needs_chunk_summarization
from brain_dump.text.tokens import estimate_tokens


def build_excerpts(facts, metrics) -> RedactedExcerpt:
    first = facts.user_messages[0].text if facts.user_messages else ""
    steering: list[str] = []
    for msg in facts.user_messages:
        if REDIRECT_PATTERN.search(msg.text) or len(msg.text) < 120:
            steering.append(redact_text(msg.text, 400))
        if len(steering) >= 3:
            break

    edits = []
    if facts.files_edited:
        edits.append(
            f"Edited {facts.files_edited} files (+{facts.lines_added}/-{facts.lines_removed} lines)"
        )
    if facts.agent_runs:
        edits.append(f"Spawned {facts.agent_runs} agent run(s)")
    if facts.tool_counts.get("CodeBlock"):
        edits.append(f"{facts.tool_counts['CodeBlock']} code block(s) in session")

    outcome = facts.title or "Session completed"
    if facts.user_messages:
        outcome = redact_text(facts.user_messages[-1].text, 300)

    full_text = read_full_transcript(facts)
    transcript_tokens = estimate_tokens(full_text)
    use_chunk_pass = needs_chunk_summarization(
        total_tokens=facts.total_tokens,
        is_structured=facts.is_structured,
        transcript_tokens=transcript_tokens,
    )

    return RedactedExcerpt(
        session_id=facts.session_id,
        first_prompt=redact_text(first, 500),
        steering_moments=steering,
        edit_summaries=edits,
        outcome_summary=outcome,
        raw_transcript=full_text if use_chunk_pass else "",
        accumulated_summary="",
        chunk_count=0,
        metrics_json={
            "steering_heuristic": metrics.steering,
            "execution_heuristic": metrics.execution,
            "tool_counts": facts.tool_counts,
            "duration_ms": facts.duration_ms,
            "total_tokens": facts.total_tokens,
            "transcript_tokens": transcript_tokens,
            "is_structured": facts.is_structured,
            "source_format": facts.source_format,
            "uses_chunk_summarization": use_chunk_pass,
        },
    )
