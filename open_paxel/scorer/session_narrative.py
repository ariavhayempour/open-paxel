from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from open_paxel.config import Settings
from open_paxel.models.domain import HeuristicMetrics, RedactedExcerpt, SessionFacts
from open_paxel.models.pipeline_models import SessionNarrative
from open_paxel.scorer.openai_tracker import tracked_openai_call
from open_paxel.text.tokens import estimate_tokens

logger = logging.getLogger(__name__)


class _SessionNarrativeLLM(BaseModel):
    summary: str = Field(description="2-4 sentence overview of the session")
    what_was_built: str = Field(description="Concrete features, fixes, or outputs")
    technologies: list[str] = Field(default_factory=list, max_length=8)
    shipped: bool = False


SYSTEM_PROMPT = """You summarize a developer's AI coding session from the full transcript.

Extract what actually happened: projects touched, features built, deployments, corrections, and outcomes.
Be specific to the transcript. Do not invent files or metrics not supported by the input."""


async def generate_session_narrative(
    facts: SessionFacts,
    metrics: HeuristicMetrics,
    excerpts: RedactedExcerpt,
    settings: Settings,
) -> SessionNarrative:
    if settings.dry_run or not excerpts.raw_transcript.strip():
        title = facts.title or "Session work"
        return SessionNarrative(
            summary=f"Dry-run summary for {title}.",
            what_was_built=title,
            technologies=[],
            shipped=bool(facts.files_edited or facts.lines_added),
        )

    key = settings.resolve_api_key()
    if not key:
        return SessionNarrative(
            summary=facts.title or "Session analyzed with heuristics only.",
            what_was_built=facts.title or "Untitled session",
            shipped=bool(facts.lines_added),
        )

    payload = {
        "title": facts.title,
        "project": facts.project_path,
        "stats": {
            "files_edited": facts.files_edited,
            "lines_added": facts.lines_added,
            "tool_errors": facts.tool_errors,
            "steering": metrics.steering,
        },
        "session_transcript": excerpts.raw_transcript,
    }
    client = AsyncOpenAI(api_key=key)
    try:
        async def _call() -> object:
            return await client.beta.chat.completions.parse(
                model=settings.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, indent=2)},
                ],
                response_format=_SessionNarrativeLLM,
            )

        completion = await tracked_openai_call(
            phase="session_narrative",
            model=settings.model,
            call=_call,
            detail=f"~{estimate_tokens(excerpts.raw_transcript)} transcript tokens",
        )
        parsed = completion.choices[0].message.parsed
        if parsed:
            return SessionNarrative.model_validate(parsed.model_dump())
    except Exception:
        logger.exception("Session narrative LLM failed for %s", facts.session_id)

    return SessionNarrative(
        summary=facts.title or "Session completed",
        what_was_built=facts.title or "Work in this session",
        shipped=bool(facts.lines_added),
    )
