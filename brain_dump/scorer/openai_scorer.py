from __future__ import annotations

import json

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from brain_dump.analysis.context import emit_progress
from brain_dump.models.domain import (
    DIMENSIONS,
    DimensionScore,
    HeuristicMetrics,
    RedactedExcerpt,
    SessionFacts,
    SessionScore,
)
from brain_dump.redact.transcript import redact_text
from brain_dump.scorer.chunk_summarizer import (
    CHUNK_SUMMARY_SYSTEM,
    chunk_summary_user_prompt,
    dry_run_chunk_summary,
)
from brain_dump.scorer.openai_tracker import tracked_openai_call
from brain_dump.text.chunking import ANALYSIS_CHUNK_TOKENS
from brain_dump.text.tokens import divide_into_chunks, estimate_tokens


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

You receive heuristic scores plus either a lossless accumulated session summary (preferred)
or short raw excerpts for small sessions.

Return honest scores 0-100 for five dimensions:
- steering: how much the user directs vs lets the agent run
- execution: code shipped, edits, tangible output
- engineering: quality, tests, error handling, discipline
- product_instinct: learning, exploration, product thinking
- planning: upfront planning, structured prompts, architecture thinking

Also assign an archetype (Architect, Quality Guardian, Velocity Machine, Night Owl, Explorer, Delegator),
2-3 signature_moves (decision patterns), growth_edge (actionable tips),
and optional insight_candidates: cryptic_prompt, crash_out, agent_relationship.

Base your judgment on the accumulated summary when provided — it already condenses the full session.
Do not invent code details not present in the input."""


class OpenAIScorer:
    def __init__(self, api_key: str, model: str, dry_run: bool = False):
        self.model = model
        self.dry_run = dry_run
        self._client = AsyncOpenAI(api_key=api_key) if not dry_run else None

    async def score_session(
        self,
        facts: SessionFacts,
        metrics: HeuristicMetrics,
        excerpts: RedactedExcerpt,
    ) -> SessionScore:
        if excerpts.raw_transcript and not excerpts.accumulated_summary:
            emit_progress(
                f"OpenAI pass 1: summarizing {facts.total_tokens} est. tokens in chunks"
            )
            excerpts.accumulated_summary, excerpts.chunk_count = await self.accumulate_chunk_summaries(
                excerpts.raw_transcript
            )
            emit_progress(
                f"OpenAI pass 1 complete: {excerpts.chunk_count} chunk(s) summarized"
            )

        if self.dry_run:
            return self._fallback_score(metrics)

        emit_progress(f"OpenAI pass 2: scoring session with {self.model}")
        return await self._score_summary(facts, metrics, excerpts)

    async def accumulate_chunk_summaries(self, text: str) -> tuple[str, int]:
        text = redact_text(text, max_len=500_000)
        chunks = divide_into_chunks(text, chunk_tokens=ANALYSIS_CHUNK_TOKENS)
        if not chunks:
            return "", 0

        accumulated = ""
        total = len(chunks)

        for index, chunk in enumerate(chunks, start=1):
            chunk_input = chunk
            est = estimate_tokens(chunk_input)
            if self.dry_run:
                accumulated = dry_run_chunk_summary(chunk_input, index, total, accumulated)
                continue

            assert self._client is not None

            async def _call(chunk_text: str = chunk_input, idx: int = index) -> object:
                return await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": CHUNK_SUMMARY_SYSTEM},
                        {
                            "role": "user",
                            "content": chunk_summary_user_prompt(
                                chunk=chunk_text,
                                prior_accumulated=accumulated,
                                index=idx,
                                total=total,
                            ),
                        },
                    ],
                    temperature=0.2,
                )

            completion = await tracked_openai_call(
                phase="chunk_summary",
                model=self.model,
                call=_call,
                chunk_index=index,
                chunk_total=total,
                detail=f"~{est} input tokens",
            )
            part = (completion.choices[0].message.content or "").strip()
            accumulated = part or accumulated

        return accumulated.strip(), total

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
            "chunk_count": excerpts.chunk_count,
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

        if excerpts.accumulated_summary:
            payload["accumulated_session_summary"] = excerpts.accumulated_summary
        else:
            payload["excerpts"] = {
                "first_prompt": excerpts.first_prompt,
                "steering_moments": excerpts.steering_moments,
                "edit_summaries": excerpts.edit_summaries,
                "outcome": excerpts.outcome_summary,
            }

        return json.dumps(payload, indent=2)

    async def _score_summary(
        self,
        facts: SessionFacts,
        metrics: HeuristicMetrics,
        excerpts: RedactedExcerpt,
    ) -> SessionScore:
        user_prompt = self.build_user_prompt(facts, metrics, excerpts)
        if self.dry_run:
            return self._fallback_score(metrics)
        assert self._client is not None

        prompt_est = estimate_tokens(user_prompt)

        async def _call() -> object:
            return await self._client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_LLMResponse,
            )

        completion = await tracked_openai_call(
            phase="session_score",
            model=self.model,
            call=_call,
            detail=f"~{prompt_est} prompt tokens",
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            return self._fallback_score(metrics)
        score = self._to_session_score(parsed)
        emit_progress(f"OpenAI scoring done: archetype={score.archetype}")
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
            growth_edge=["Enable OpenAI scoring for richer feedback"],
            insight_candidates={},
        )
