from __future__ import annotations

from collections import Counter

from open_paxel.decisions.catalog import resolve_catalog_match
from open_paxel.models.domain import SessionReport
from open_paxel.models.pipeline_models import Decision
from open_paxel.redact.transcript import redact_text


def link_decision_outcomes(
    decisions: list[Decision],
    reports_by_id: dict[str, SessionReport],
) -> list[Decision]:
    linked: list[Decision] = []
    for decision in decisions:
        report = reports_by_id.get(decision.session_id)
        outcome = None
        if report:
            if report.git_commit_ids:
                outcome = f"Linked to {len(report.git_commit_ids)} commit(s)"
            elif report.session_narrative and report.session_narrative.shipped:
                outcome = "Session narrative marked shipped"
            elif report.heuristic_metrics and report.heuristic_metrics.lines_added:
                outcome = f"+{report.heuristic_metrics.lines_added} lines edited"
        linked.append(decision.model_copy(update={"outcome_link": outcome}))
    return linked


def redact_decisions(decisions: list[Decision]) -> list[Decision]:
    return [
        d.model_copy(
            update={
                "summary": redact_text(d.summary, 400),
                "evidence_quote": redact_text(d.evidence_quote, 300),
            }
        )
        for d in decisions
    ]


def enrich_catalog_fields(decisions: list[Decision]) -> list[Decision]:
    enriched: list[Decision] = []
    for d in decisions:
        pattern = resolve_catalog_match(d.catalog_key)
        if pattern:
            enriched.append(
                d.model_copy(
                    update={
                        "catalog_title": pattern.title,
                        "catalog_category": pattern.category,
                    }
                )
            )
        else:
            enriched.append(d.model_copy(update={"catalog_key": None}))
    return enriched


def aggregate_decisions(decisions: list[Decision]) -> dict[str, object]:
    exchange_counts = Counter(d.exchange_type for d in decisions)
    catalog_counts = Counter(d.catalog_key for d in decisions if d.catalog_key)
    top_catalog = catalog_counts.most_common(1)[0][0] if catalog_counts else None
    top_pattern = resolve_catalog_match(top_catalog)
    return {
        "total": len(decisions),
        "by_exchange_type": dict(exchange_counts),
        "by_catalog_key": dict(catalog_counts),
        "top_catalog_key": top_catalog,
        "top_catalog_title": top_pattern.title if top_pattern else None,
        "top_catalog_category": top_pattern.category if top_pattern else None,
    }
