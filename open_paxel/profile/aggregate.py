from __future__ import annotations

from typing import TYPE_CHECKING

from open_paxel.decisions.stats import aggregate_decisions
from open_paxel.models.domain import (
    DIMENSIONS,
    BuilderProfile,
    InsightCard,
    SessionReport,
    UploadReport,
)
from open_paxel.profile.insights import build_insight_cards, collect_profile_signals
from open_paxel.profile.narrative_heuristic import build_profile_narrative

if TYPE_CHECKING:
    from open_paxel.pipeline.context import PipelineContext


def build_profile(
    reports: list[SessionReport],
    uploads: list[UploadReport],
    *,
    pipeline_ctx: PipelineContext | None = None,
) -> BuilderProfile:
    if not reports:
        from datetime import datetime

        return BuilderProfile(
            updated_at=datetime.utcnow(),
            insight_cards=[
                InsightCard(
                    id="empty",
                    question="Ready to analyze?",
                    title="Get started",
                    value="Run open-paxel upload",
                    subtitle="Analyze your Claude Code sessions locally",
                )
            ],
        )

    from collections import Counter
    from datetime import datetime

    dim_sums: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    all_moves: list[str] = []
    all_growth: list[str] = []

    for report in reports:
        all_moves.extend(report.signature_moves)
        all_growth.extend(report.growth_edge)
        for dim in DIMENSIONS:
            if dim in report.dimensions:
                dim_sums[dim].append(report.dimensions[dim].score)

    signals = collect_profile_signals(reports)
    top_archetype = signals.archetypes.most_common(1)[0][0] if signals.archetypes else "Explorer"
    dimensions = {d: round(sum(v) / len(v), 1) if v else 0.0 for d, v in dim_sums.items()}

    if pipeline_ctx and pipeline_ctx.episodes:
        scored = [e for e in pipeline_ctx.episodes if not e.skipped and e.dimensions]
        if scored:
            dim_sums = {d: [] for d in DIMENSIONS}
            for episode in scored:
                for dim in DIMENSIONS:
                    if dim in episode.dimensions:
                        dim_sums[dim].append(episode.dimensions[dim].score)
            dimensions = {d: round(sum(v) / len(v), 1) if v else 0.0 for d, v in dim_sums.items()}

    move_counts = Counter(all_moves)
    growth_counts = Counter(all_growth)
    signature_moves = [m for m, _ in move_counts.most_common(5)]
    growth_edge_list = [g for g, _ in growth_counts.most_common(3)]

    all_decisions = []
    for report in reports:
        all_decisions.extend(report.decisions)
    if pipeline_ctx and pipeline_ctx.decisions:
        all_decisions = pipeline_ctx.decisions
    decision_stats = aggregate_decisions(all_decisions)

    narrative = build_profile_narrative(
        reports,
        signals,
        archetype=top_archetype,
        signature_moves=signature_moves,
        growth_edge=growth_edge_list,
        decision_stats=decision_stats,
        episodes=pipeline_ctx.episodes if pipeline_ctx else [],
    )

    insight_cards = build_insight_cards(signals, decision_stats=decision_stats)

    profile = BuilderProfile(
        updated_at=datetime.utcnow(),
        session_count=len(reports),
        upload_count=len(uploads),
        dimensions=dimensions,
        archetype=top_archetype,
        archetype_counts=dict(signals.archetypes),
        signature_moves=signature_moves,
        growth_edge=growth_edge_list,
        insight_cards=insight_cards,
        narrative=narrative,
    )
    if pipeline_ctx:
        profile = profile.model_copy(
            update={
                "episodes": pipeline_ctx.episodes,
                "pipeline_artifacts": pipeline_ctx.artifacts(),
            }
        )
    return profile
