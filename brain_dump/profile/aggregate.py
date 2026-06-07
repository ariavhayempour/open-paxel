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


def build_profile(reports: list[SessionReport], uploads: list[UploadReport]) -> BuilderProfile:
    if not reports:
        return BuilderProfile(
            updated_at=datetime.utcnow(),
            insight_cards=[
                InsightCard(
                    id="empty",
                    title="Get started",
                    value="Run brain-dump upload",
                    subtitle="Analyze your Claude Code sessions locally",
                )
            ],
        )

    dim_sums: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    archetypes: Counter[str] = Counter()
    all_moves: list[str] = []
    all_growth: list[str] = []
    model_counts: Counter[str] = Counter()
    plan_sessions = 0
    hour_hist: Counter[int] = Counter()
    cryptic: str | None = None
    crash: str | None = None
    relationship: str | None = None
    go_to_phrase: str | None = None

    for r in reports:
        archetypes[r.archetype] += 1
        all_moves.extend(r.signature_moves)
        all_growth.extend(r.growth_edge)
        hm = r.heuristic_metrics
        if hm:
            if hm.plan_mode_used:
                plan_sessions += 1
            if hm.primary_model:
                model_counts[hm.primary_model] += 1
            for h, c in hm.hour_histogram.items():
                hour_hist[h] += c
            if hm.top_phrases and not go_to_phrase:
                go_to_phrase = hm.top_phrases[0][0]
        for dim in DIMENSIONS:
            if dim in r.dimensions:
                dim_sums[dim].append(r.dimensions[dim].score)
        ic = r.insight_candidates or {}
        cryptic = cryptic or ic.get("cryptic_prompt")
        crash = crash or ic.get("crash_out")
        relationship = relationship or ic.get("agent_relationship")

    dimensions = {d: round(sum(v) / len(v), 1) if v else 0.0 for d, v in dim_sums.items()}
    top_archetype = archetypes.most_common(1)[0][0] if archetypes else "Explorer"

    move_counts = Counter(all_moves)
    growth_counts = Counter(all_growth)

    cards: list[InsightCard] = [
        InsightCard(id="archetype", title="Archetype", value=top_archetype),
    ]

    if model_counts:
        top_model, count = model_counts.most_common(1)[0]
        pct = round(100 * count / len(reports))
        cards.append(
            InsightCard(
                id="model",
                title="Top model",
                value=top_model,
                subtitle=f"Used in {pct}% of sessions",
            )
        )

    if hour_hist:
        night = sum(hour_hist[h] for h in list(hour_hist) if h >= 22 or h < 6)
        total_h = sum(hour_hist.values())
        if total_h and night / total_h >= 0.4:
            cards.append(
                InsightCard(id="productivity", title="Productivity", value="Night owl", subtitle="Most sessions after 10 PM")
            )

    if reports:
        plan_pct = round(100 * plan_sessions / len(reports))
        cards.append(
            InsightCard(id="plan", title="Plan mode", value=f"{plan_pct}%", subtitle="Sessions with plan mode")
        )

    if go_to_phrase:
        cards.append(InsightCard(id="goto", title="Go-to phrase", value=go_to_phrase))

    if cryptic:
        cards.append(InsightCard(id="cryptic", title="Cryptic prompt", value=cryptic[:80]))
    if crash:
        cards.append(InsightCard(id="crash", title="Biggest crash out", value=crash[:80]))
    if relationship:
        cards.append(InsightCard(id="relationship", title="Agent relationship", value=relationship))

    return BuilderProfile(
        updated_at=datetime.utcnow(),
        session_count=len(reports),
        upload_count=len(uploads),
        dimensions=dimensions,
        archetype=top_archetype,
        archetype_counts=dict(archetypes),
        signature_moves=[m for m, _ in move_counts.most_common(5)],
        growth_edge=[g for g, _ in growth_counts.most_common(3)],
        insight_cards=cards,
    )
