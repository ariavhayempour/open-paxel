from __future__ import annotations

import json

from pydantic import BaseModel, Field

from open_paxel.analysis.context import emit_progress
from open_paxel.config import Settings
from open_paxel.llm.client import create_async_llm_client, llm_provider_label
from open_paxel.llm.structured import parse_structured_completion
from open_paxel.models.domain import (
    DIMENSIONS,
    DimensionScore,
    HeuristicMetrics,
    RedactedExcerpt,
    SessionFacts,
    SessionScore,
)
from open_paxel.scorer.openai_tracker import tracked_openai_call
from open_paxel.text.tokens import estimate_tokens


class _LLMDimension(BaseModel):
    score: float = Field(ge=0, le=100)
    narrative: str = ""
    evidence: list[str] = Field(default_factory=list)


class _LLMResponse(BaseModel):
    steering: _LLMDimension
    execution: _LLMDimension
    engineering: _LLMDimension
    product_instinct: _LLMDimension
    planning: _LLMDimension
    archetype: str = "Explorer"
    signature_moves: list[str] = Field(default_factory=list)
    growth_edge: list[str] = Field(default_factory=list)
    cryptic_prompt: str | None = None
    crash_out: str | None = None
    agent_relationship: str | None = None


SYSTEM_PROMPT = """You score how a developer works with an AI coding assistant in a session.

You receive the full redacted session transcript plus heuristic scores and session stats.
Read the transcript and decide what matters for scoring — do not rely on pre-summarized input.

Return honest scores 0-100 for five dimensions:
- steering: how much the user directs vs lets the agent run
- execution: code shipped, edits, tangible output
- engineering: quality, tests, error handling, discipline
- product_instinct: learning, exploration, product thinking
- planning: upfront planning, structured prompts, architecture thinking

Also assign an archetype (Architect, Quality Guardian, Velocity Machine, Night Owl, Explorer, Delegator),
2-3 signature_moves (decision patterns), growth_edge (actionable tips),
and optional insight_candidates: cryptic_prompt, crash_out, agent_relationship.

Focus on evidence from the transcript. Do not invent code details not present in the input."""


class OpenAIScorer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.effective_model()
        self.dry_run = settings.dry_run
        self._client = create_async_llm_client(settings)

    async def score_session(
        self,
        facts: SessionFacts,
        metrics: HeuristicMetrics,
        excerpts: RedactedExcerpt,
    ) -> SessionScore:
        if self.dry_run or self._client is None:
            return self._fallback_score(metrics)

        transcript = excerpts.raw_transcript.strip()
        est = estimate_tokens(transcript) if transcript else facts.total_tokens
        label = llm_provider_label(self.settings)
        emit_progress(f"{label}: scoring full session (~{est} est. tokens) with {self.model}")
        return await self._score_session(facts, metrics, excerpts)

    def build_user_prompt(
        self, facts: SessionFacts, metrics: HeuristicMetrics, excerpts: RedactedExcerpt
    ) -> str:
        payload: dict = {
            "session_id": facts.session_id,
            "title": facts.title,
            "project": facts.project_path,
            "source_format": facts.source_format,
            "is_structured": facts.is_structured,
            "total_tokens": facts.total_tokens,
            "transcript_tokens": excerpts.metrics_json.get("transcript_tokens"),
            "transcript_truncated": excerpts.metrics_json.get("transcript_truncated", False),
            "duration_minutes": round(facts.duration_ms / 60000, 1),
            "heuristic_scores": {
                "steering": metrics.steering,
                "execution": metrics.execution,
                "engineering": metrics.engineering,
                "product_instinct": metrics.product_instinct,
                "planning": metrics.planning,
            },
            "stats": {
                "user_messages": len(facts.user_messages),
                "estimated_turns": facts.raw_turn_count,
                "lines_added": facts.lines_added,
                "files_edited": facts.files_edited,
                "plan_mode": metrics.plan_mode_used,
                "tool_errors": facts.tool_errors,
            },
        }

        if excerpts.raw_transcript.strip():
            payload["session_transcript"] = excerpts.raw_transcript
        else:
            payload["excerpts"] = {
                "first_prompt": excerpts.first_prompt,
                "steering_moments": excerpts.steering_moments,
                "edit_summaries": excerpts.edit_summaries,
                "outcome": excerpts.outcome_summary,
            }

        return json.dumps(payload, indent=2)

    async def _score_session(
        self,
        facts: SessionFacts,
        metrics: HeuristicMetrics,
        excerpts: RedactedExcerpt,
    ) -> SessionScore:
        user_prompt = self.build_user_prompt(facts, metrics, excerpts)
        assert self._client is not None

        prompt_est = estimate_tokens(user_prompt)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        async def _call() -> _LLMResponse | None:
            return await parse_structured_completion(
                self._client,
                settings=self.settings,
                model=self.model,
                messages=messages,
                response_model=_LLMResponse,
            )

        parsed = await tracked_openai_call(
            phase="session_score",
            model=self.model,
            call=_call,
            detail=f"~{prompt_est} prompt tokens",
        )
        if parsed is None:
            return self._fallback_score(metrics)
        score = self._to_session_score(parsed)
        emit_progress(f"{llm_provider_label(self.settings)} scoring done: archetype={score.archetype}")
        return score

    def _to_session_score(self, parsed: _LLMResponse) -> SessionScore:
        dimensions: dict[str, DimensionScore] = {}
        for dim in DIMENSIONS:
            d = getattr(parsed, dim)
            dimensions[dim] = DimensionScore(
                score=d.score, narrative=d.narrative, evidence=d.evidence[:3]
            )
        return SessionScore(
            dimensions=dimensions,
            archetype=parsed.archetype,
            signature_moves=parsed.signature_moves[:5],
            growth_edge=parsed.growth_edge[:3],
            insight_candidates={
                "cryptic_prompt": parsed.cryptic_prompt,
                "crash_out": parsed.crash_out,
                "agent_relationship": parsed.agent_relationship,
            },
        )

    def _fallback_score(self, metrics: HeuristicMetrics) -> SessionScore:
        dimensions = {
            dim: DimensionScore(
                score=getattr(metrics, dim),
                narrative="Heuristic-only (dry run or LLM unavailable)",
                evidence=[],
            )
            for dim in DIMENSIONS
        }
        return SessionScore(
            dimensions=dimensions,
            archetype="Explorer",
            signature_moves=["Iterates with short prompts"],
            growth_edge=["Enable LLM scoring for richer feedback"],
            insight_candidates={},
        )
