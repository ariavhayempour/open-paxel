from __future__ import annotations

from collections import Counter
from datetime import datetime

from brain_dump.models.domain import (
    DIMENSIONS,
    BuilderProfile,
    InsightCard,
    SessionReport,
    UploadReport,
)
from brain_dump.profile.insights import build_insight_cards, collect_profile_signals


def build_profile(reports: list[SessionReport], uploads: list[UploadReport]) -> BuilderProfile:
    if not reports:
        return BuilderProfile(
            updated_at=datetime.utcnow(),
            insight_cards=[
                InsightCard(
                    id="empty",
                    question="Ready to analyze?",
                    title="Get started",
                    value="Run brain-dump upload",
                    subtitle="Analyze your Claude Code sessions locally",
                )
            ],
        )

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

    move_counts = Counter(all_moves)
    growth_counts = Counter(all_growth)

    return BuilderProfile(
        updated_at=datetime.utcnow(),
        session_count=len(reports),
        upload_count=len(uploads),
        dimensions=dimensions,
        archetype=top_archetype,
        archetype_counts=dict(signals.archetypes),
        signature_moves=[m for m, _ in move_counts.most_common(5)],
        growth_edge=[g for g, _ in growth_counts.most_common(3)],
        insight_cards=build_insight_cards(signals),
    )
