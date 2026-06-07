from __future__ import annotations

import json
import logging
import uuid

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from open_paxel.config import Settings
from open_paxel.models.domain import DIMENSIONS, SessionReport
from open_paxel.models.pipeline_models import Episode, WorkStream
from open_paxel.models.scores import DimensionScore
from open_paxel.scorer.openai_tracker import tracked_openai_call

logger = logging.getLogger(__name__)


class _EpisodeDimension(BaseModel):
    score: float = Field(ge=0, le=100)
    narrative: str = ""


class _EpisodeScoreLLM(BaseModel):
    title: str = ""
    steering: _EpisodeDimension
    execution: _EpisodeDimension
    engineering: _EpisodeDimension
    product_instinct: _EpisodeDimension
    planning: _EpisodeDimension
    narrative: str = ""


SYSTEM_PROMPT = """Score a multi-session work episode (work stream) across five builder dimensions.

Use session narratives, git activity, and decision patterns. Skip generic praise.
Return honest 0-100 scores with brief narratives."""


def _episode_payload(
    stream: WorkStream,
    reports: list[SessionReport],
    *,
    code_quality_label: str | None,
    decision_summaries: list[str],
) -> dict:
    sessions = []
    for report in reports:
        sessions.append(
            {
                "session_id": report.session_id,
                "title": report.title,
                "narrative": report.session_narrative.model_dump() if report.session_narrative else None,
                "commits": report.git_commit_ids,
                "lines_added": report.heuristic_metrics.lines_added if report.heuristic_metrics else 0,
            }
        )
    return {
        "work_stream": stream.model_dump(mode="json"),
        "sessions": sessions,
        "code_quality": code_quality_label,
        "decisions": decision_summaries[:10],
    }


def _heuristic_episode(
    stream: WorkStream,
    reports: list[SessionReport],
) -> Episode:
    dims: dict[str, DimensionScore] = {}
    for dim in DIMENSIONS:
        scores = [r.dimensions[dim].score for r in reports if dim in r.dimensions]
        avg = sum(scores) / len(scores) if scores else 50.0
        dims[dim] = DimensionScore(score=avg, narrative="Heuristic episode rollup")
    title = reports[0].title if reports and reports[0].title else "Work stream"
    return Episode(
        id=str(uuid.uuid4()),
        work_stream_id=stream.id,
        title=title,
        session_ids=stream.session_ids,
        dimensions=dims,
        narrative="Episode scored from session heuristics.",
    )


async def score_episode(
    stream: WorkStream,
    reports: list[SessionReport],
    *,
    settings: Settings,
    code_quality_label: str | None,
    decision_summaries: list[str],
) -> Episode:
    stream_reports = [r for r in reports if r.session_id in stream.session_ids]
    if not stream_reports:
        return Episode(
            id=str(uuid.uuid4()),
            work_stream_id=stream.id,
            session_ids=stream.session_ids,
            skipped=True,
            skip_reason="no evidence",
        )

    has_signal = any(
        r.session_narrative
        or r.git_commit_ids
        or (r.heuristic_metrics and r.heuristic_metrics.lines_added)
        for r in stream_reports
    )
    if not has_signal:
        return Episode(
            id=str(uuid.uuid4()),
            work_stream_id=stream.id,
            session_ids=stream.session_ids,
            skipped=True,
            skip_reason="no evidence",
        )

    if settings.dry_run:
        return _heuristic_episode(stream, stream_reports)

    key = settings.resolve_api_key()
    if not key:
        return _heuristic_episode(stream, stream_reports)

    payload = _episode_payload(
        stream,
        stream_reports,
        code_quality_label=code_quality_label,
        decision_summaries=decision_summaries,
    )
    client = AsyncOpenAI(api_key=key)
    try:
        async def _call() -> object:
            return await client.beta.chat.completions.parse(
                model=settings.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, indent=2)},
                ],
                response_format=_EpisodeScoreLLM,
            )

        completion = await tracked_openai_call(
            phase="episode_scoring",
            model=settings.model,
            call=_call,
            detail=f"{len(stream_reports)} sessions",
        )
        parsed = completion.choices[0].message.parsed
        if not parsed:
            return _heuristic_episode(stream, stream_reports)

        dimensions = {
            dim: DimensionScore(
                score=getattr(parsed, dim).score,
                narrative=getattr(parsed, dim).narrative,
            )
            for dim in DIMENSIONS
        }
        return Episode(
            id=str(uuid.uuid4()),
            work_stream_id=stream.id,
            title=parsed.title or (stream_reports[0].title or "Work episode"),
            session_ids=stream.session_ids,
            dimensions=dimensions,
            narrative=parsed.narrative,
        )
    except Exception:
        logger.exception("Episode scoring failed for stream %s", stream.id)
        return _heuristic_episode(stream, stream_reports)
