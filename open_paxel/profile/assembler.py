from __future__ import annotations

from typing import TYPE_CHECKING

from open_paxel.config import Settings
from open_paxel.decisions.stats import aggregate_decisions
from open_paxel.models.domain import DIMENSIONS, BuilderProfile, SessionReport
from open_paxel.models.pipeline_models import PipelineArtifacts
from open_paxel.profile.aggregate import build_profile

if TYPE_CHECKING:
    from open_paxel.pipeline.context import PipelineContext


async def assemble_profile(
    settings: Settings,
    repository,
    ctx: PipelineContext,
) -> BuilderProfile:
    from open_paxel.profile.enrich import enrich_profile_narrative

    reports = repository.list_reports(limit=10_000)
    uploads = repository.list_uploads()
    profile = build_profile(reports, uploads, pipeline_ctx=ctx)

    artifacts = ctx.artifacts()
    episode_dims = _episode_dimensions(artifacts)
    if episode_dims:
        profile = profile.model_copy(update={"dimensions": episode_dims})

    profile = profile.model_copy(
        update={
            "episodes": artifacts.episodes,
            "pipeline_artifacts": artifacts,
        }
    )

    llm_narrative = await enrich_profile_narrative(settings, repository, pipeline_ctx=ctx)
    if llm_narrative:
        profile = profile.model_copy(update={"narrative": llm_narrative})

    repository.save_profile_cache(profile)
    if ctx.upload_id:
        repository.save_upload_artifacts(ctx.upload_id, artifacts)
    return profile


def _episode_dimensions(artifacts: PipelineArtifacts) -> dict[str, float]:
    scored = [e for e in artifacts.episodes if not e.skipped and e.dimensions]
    if not scored:
        return {}
    dim_sums: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for episode in scored:
        for dim in DIMENSIONS:
            if dim in episode.dimensions:
                dim_sums[dim].append(episode.dimensions[dim].score)
    return {d: round(sum(v) / len(v), 1) if v else 0.0 for d, v in dim_sums.items()}


def decision_stats_from_reports(reports: list[SessionReport]) -> dict[str, object]:
    all_decisions = []
    for report in reports:
        all_decisions.extend(report.decisions)
    return aggregate_decisions(all_decisions)
