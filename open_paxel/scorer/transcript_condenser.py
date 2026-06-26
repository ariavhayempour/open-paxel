from __future__ import annotations

import logging

from open_paxel.config import Settings
from open_paxel.llm.client import create_async_llm_client, llm_provider_label
from open_paxel.scorer.chunk_summarizer import (
    CHUNK_SUMMARY_SYSTEM,
    chunk_summary_user_prompt,
    dry_run_chunk_summary,
)
from open_paxel.scorer.openai_tracker import tracked_openai_call
from open_paxel.text.tokens import estimate_tokens
from open_paxel.analysis.context import emit_progress

logger = logging.getLogger(__name__)


def needs_condensing(full_text: str, settings: Settings) -> bool:
    """True when the transcript is too large to send raw to the scoring model."""
    return estimate_tokens(full_text) > settings.condense_over_est_tokens


def _char_chunks(text: str, chunk_chars: int) -> list[str]:
    """Split text into <=chunk_chars pieces, preferring newline boundaries.

    Sized by characters, not estimated tokens: estimate_tokens under-counts dense
    JSONL by ~6x, so a token-sized chunk overflows the model. A character budget
    is a safe upper bound (worst case ~1 token/char for minified content).
    """
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    i, n = 0, len(text)
    while i < n:
        end = min(n, i + chunk_chars)
        if end < n:
            nl = text.rfind("\n", i + chunk_chars // 2, end)
            if nl != -1:
                end = nl
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        i = end
    return chunks


def _sample_chunks(chunks: list[str], cap: int) -> tuple[list[str], bool]:
    """Keep first, last, and evenly spaced middle chunks when over the cap."""
    if len(chunks) <= cap:
        return chunks, False
    keep = {0, len(chunks) - 1}
    inner = max(0, cap - 2)
    for k in range(inner):
        keep.add(round((k + 1) * (len(chunks) - 1) / (inner + 1)))
    return [chunks[i] for i in sorted(keep)], True


async def condense_transcript(full_text: str, settings: Settings) -> tuple[str, int]:
    """Compress an oversized transcript into a lossless running summary.

    Splits the transcript into context-sized chunks and folds each into an
    accumulating summary, so the scorer sees the *whole* session (not just its
    truncated head) without overflowing the model's context window. Returns
    ``(summary, chunk_count)``; on any failure returns ``("", 0)`` so the caller
    falls back to the existing truncated-transcript behavior.
    """
    all_chunks = _char_chunks(full_text, settings.condense_chunk_chars)
    if not all_chunks:
        return "", 0
    chunks, sampled = _sample_chunks(all_chunks, settings.condense_max_chunks)

    if settings.dry_run or not settings.llm_configured():
        accumulated = ""
        for i, chunk in enumerate(chunks, 1):
            accumulated = dry_run_chunk_summary(chunk, i, len(chunks), accumulated)
        return accumulated, len(chunks)

    client = create_async_llm_client(settings)
    if client is None:
        return "", 0

    model = settings.effective_model()
    label = llm_provider_label(settings)
    if sampled:
        emit_progress(
            f"{label}: transcript too large — condensing {len(chunks)} representative "
            f"of {len(all_chunks)} chunks with {model}"
        )
    else:
        emit_progress(
            f"{label}: condensing oversized transcript ({len(chunks)} chunks) with {model}"
        )

    accumulated = ""
    for i, chunk in enumerate(chunks, 1):
        messages = [
            {"role": "system", "content": CHUNK_SUMMARY_SYSTEM},
            {
                "role": "user",
                "content": chunk_summary_user_prompt(
                    chunk=chunk, prior_accumulated=accumulated, index=i, total=len(chunks)
                ),
            },
        ]

        async def _call() -> str:
            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=settings.max_output_tokens,
            )
            return completion.choices[0].message.content or ""

        try:
            content = await tracked_openai_call(
                phase="transcript_condense",
                model=model,
                call=_call,
                detail=f"chunk {i}/{len(chunks)}",
            )
        except Exception:
            logger.exception("Transcript condensing failed on chunk %d/%d", i, len(chunks))
            return (accumulated, i - 1) if accumulated else ("", 0)

        if content and content.strip():
            accumulated = content.strip()

    return accumulated, len(chunks)
