from __future__ import annotations

from typing import TYPE_CHECKING

from open_paxel.config import Settings
from open_paxel.db.repository import SQLiteRepository
from open_paxel.decisions.stats import aggregate_decisions
from open_paxel.models.profile_narrative import ProfileNarrative
from open_paxel.profile.aggregate import build_profile
from open_paxel.profile.narrative_llm import generate_profile_narrative_llm

if TYPE_CHECKING:
    from open_paxel.pipeline.context import PipelineContext


async def enrich_profile_narrative(
    settings: Settings,
    repo: SQLiteRepository,
    *,
    pipeline_ctx: PipelineContext | None = None,
) -> ProfileNarrative | None:
    reports = repo.list_reports(limit=10_000)
    uploads = repo.list_uploads()
    profile = build_profile(reports, uploads, pipeline_ctx=pipeline_ctx)

    all_decisions = pipeline_ctx.decisions if pipeline_ctx else []
    if not all_decisions:
        for report in reports:
            all_decisions.extend(report.decisions)
    decision_stats = aggregate_decisions(all_decisions)

    llm_narrative = await generate_profile_narrative_llm(
        reports,
        settings,
        decision_stats=decision_stats,
        episodes=pipeline_ctx.episodes if pipeline_ctx else profile.episodes,
    )
    if llm_narrative:
        return llm_narrative
    return profile.narrative
