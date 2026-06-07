from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from brain_dump.metrics.heuristics import blend_dimension, compute_heuristics
from brain_dump.models.domain import DIMENSIONS, SessionReport
from brain_dump.parser.auto import AutoTranscriptParser
from brain_dump.redact.excerpts import build_excerpts
from brain_dump.scorer.registry import get_scorer
from brain_dump.config import Settings

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    def __init__(self, settings: Settings, repository, parser=None, scorer=None):
        self.settings = settings
        self.repository = repository
        self.parser = parser or AutoTranscriptParser()
        self._scorer = scorer

    def _get_scorer(self):
        if self._scorer is None:
            self._scorer = get_scorer(self.settings)
        return self._scorer

    async def analyze_file(
        self, path: Path, upload_id: str | None = None, force: bool = False
    ) -> SessionReport:
        path = Path(path)
        logger.info("Parsing %s", path.name)
        facts = self.parser.parse(path)
        logger.debug(
            "Parsed session_id=%s tokens=%s structured=%s",
            facts.session_id,
            facts.total_tokens,
            facts.is_structured,
        )

        if (
            not force
            and self.repository.report_exists(facts.session_id)
            and not self.settings.dry_run
        ):
            existing = self.repository.get_report(facts.session_id)
            if existing:
                logger.info("Cache hit for session %s", facts.session_id)
                return existing

        logger.info("Computing heuristics for %s", facts.session_id)
        metrics = compute_heuristics(facts)
        excerpts = build_excerpts(facts, metrics)
        scorer = self._get_scorer()
        logger.info("LLM scoring %s", facts.session_id)
        llm_score = await scorer.score_session(facts, metrics, excerpts)

        dimensions = {}
        for dim in DIMENSIONS:
            h = getattr(metrics, dim)
            llm_dim = llm_score.dimensions.get(dim)
            llm_val = llm_dim.score if llm_dim else h
            weight = 0.5 if dim in ("engineering", "product_instinct") else 0.4
            blended = blend_dimension(h, llm_val, heuristic_weight=weight)
            narrative = llm_dim.narrative if llm_dim else ""
            evidence = llm_dim.evidence if llm_dim else []
            from brain_dump.models.domain import DimensionScore

            dimensions[dim] = DimensionScore(score=blended, narrative=narrative, evidence=evidence)

        report = SessionReport(
            session_id=facts.session_id,
            transcript_path=str(path),
            project_path=facts.project_path,
            title=facts.title,
            analyzed_at=datetime.utcnow(),
            dimensions=dimensions,
            archetype=llm_score.archetype,
            signature_moves=llm_score.signature_moves,
            growth_edge=llm_score.growth_edge,
            insight_candidates=llm_score.insight_candidates,
            heuristic_metrics=metrics,
            upload_id=upload_id,
        )

        if not self.settings.dry_run:
            self.repository.save_report(report)
        logger.info("Saved report %s (%s)", report.session_id, report.title or "Untitled")
        return report
