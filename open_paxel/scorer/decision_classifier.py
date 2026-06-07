from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from open_paxel.config import Settings
from open_paxel.decisions.catalog import catalog_by_key, compact_catalog_for_prompt
from open_paxel.models.domain import SessionReport
from open_paxel.models.pipeline_models import Decision
from open_paxel.scorer.openai_tracker import tracked_openai_call

logger = logging.getLogger(__name__)

EXCHANGE_TYPES = ("strategic_redirect", "technical_catch", "scope_change", "clarification")


class _DecisionItem(BaseModel):
    session_id: str
    exchange_type: str
    catalog_key: str | None = None
    summary: str = ""
    evidence_quote: str = ""


class _DecisionBatch(BaseModel):
    decisions: list[_DecisionItem] = Field(default_factory=list, max_length=20)


SYSTEM_PROMPT = """You classify developer steering moments in AI coding sessions.

For each steering trace, decide if it is a meaningful decision exchange.
If yes, assign:
- exchange_type: one of strategic_redirect, technical_catch, scope_change, clarification
- catalog_key: best matching pattern key from the catalog, or null if none fit well
- summary: one sentence on what the builder decided
- evidence_quote: short quote from the trace

Only use catalog_key values from the provided catalog. Do not invent keys."""


def _dry_run_decisions(reports: list[SessionReport]) -> list[Decision]:
    decisions: list[Decision] = []
    for report in reports:
        for trace in report.steering_traces[:3]:
            decisions.append(
                Decision(
                    session_id=report.session_id,
                    exchange_type="strategic_redirect",
                    summary=trace.text[:120],
                    evidence_quote=trace.text[:200],
                )
            )
    return decisions


async def classify_decisions(
    reports: list[SessionReport],
    settings: Settings,
) -> list[Decision]:
    traces = []
    for report in reports:
        for trace in report.steering_traces:
            traces.append(
                {
                    "session_id": report.session_id,
                    "text": trace.text,
                    "after_tool": trace.after_tool,
                    "narrative": (report.session_narrative.summary if report.session_narrative else ""),
                }
            )
    if not traces:
        return []
    if settings.dry_run:
        return _dry_run_decisions(reports)

    key = settings.resolve_api_key()
    if not key:
        return _dry_run_decisions(reports)

    valid_keys = set(catalog_by_key().keys())
    payload = {
        "steering_traces": traces[:40],
        "catalog": compact_catalog_for_prompt(),
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
                response_format=_DecisionBatch,
            )

        completion = await tracked_openai_call(
            phase="decision_classifier",
            model=settings.model,
            call=_call,
            detail=f"{len(traces)} traces",
        )
        parsed = completion.choices[0].message.parsed
        if not parsed:
            return _dry_run_decisions(reports)

        decisions: list[Decision] = []
        for item in parsed.decisions:
            if item.exchange_type not in EXCHANGE_TYPES:
                item.exchange_type = "strategic_redirect"
            catalog_key = item.catalog_key if item.catalog_key in valid_keys else None
            decisions.append(
                Decision(
                    session_id=item.session_id,
                    exchange_type=item.exchange_type,
                    catalog_key=catalog_key,
                    summary=item.summary,
                    evidence_quote=item.evidence_quote,
                )
            )
        return decisions
    except Exception:
        logger.exception("Decision classifier failed")
        return _dry_run_decisions(reports)
