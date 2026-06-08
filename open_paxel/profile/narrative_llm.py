from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from open_paxel.config import Settings
from open_paxel.llm.client import create_async_llm_client
from open_paxel.llm.structured import parse_structured_completion
from open_paxel.models.domain import SessionReport
from open_paxel.models.profile_narrative import ProfileNarrative

logger = logging.getLogger(__name__)


class _LLMProfileNarrative(BaseModel):
    narrative: str = Field(description="2-3 sentence overview of how the developer uses Claude Code")
    what_you_built: str = Field(description="Paragraph on projects, outputs, and shipped work")
    decision_patterns: str = Field(
        description="Paragraph on decision style, architecture focus, corrections, and steering"
    )
    matched_pattern: str | None = Field(
        default=None, description="Short name for the dominant decision pattern, if clear"
    )
    matched_pattern_category: str | None = Field(
        default=None, description="Category for matched pattern, e.g. Code & Architecture"
    )
    strengths: list[str] = Field(default_factory=list, max_length=4)
    growth_areas: list[str] = Field(default_factory=list, max_length=3)


SYSTEM_PROMPT = """You write a builder profile narrative from analyzed Claude Code sessions.

Match this structure and tone (Paxel-style):
- narrative: overall how they use Claude Code (implementation engine vs planner, control vs delegation)
- what_you_built: concrete projects, features, deployments, domain work
- decision_patterns: architecture-heavy vs exploratory, technical catches, scope control; name a matched pattern if evident
- strengths: 2-4 specific bullets citing session evidence
- growth_areas: 2-3 actionable bullets with concrete next steps

Be specific to the session data. Do not invent repos, files, or metrics not supported by the input."""


def _session_payload(
    reports: list[SessionReport],
    *,
    decision_stats: dict[str, object] | None = None,
    episodes: list | None = None,
) -> str:
    items = []
    for r in reports[:20]:
        dims = {k: v.score for k, v in r.dimensions.items()}
        items.append(
            {
                "title": r.title,
                "project": r.project_path,
                "archetype": r.archetype,
                "dimensions": dims,
                "session_narrative": r.session_narrative.model_dump() if r.session_narrative else None,
                "decisions": [d.model_dump() for d in r.decisions[:5]],
                "signature_moves": r.signature_moves,
                "growth_edge": r.growth_edge,
            }
        )
    payload = {
        "sessions": items,
        "decision_stats": decision_stats or {},
        "episodes": [e.model_dump() for e in (episodes or [])[:10]],
    }
    return json.dumps(payload, indent=2)


async def generate_profile_narrative_llm(
    reports: list[SessionReport],
    settings: Settings,
    *,
    decision_stats: dict[str, object] | None = None,
    episodes: list | None = None,
) -> ProfileNarrative | None:
    if not reports or settings.dry_run or not settings.llm_configured():
        return None

    client = create_async_llm_client(settings)
    if client is None:
        return None

    model = settings.effective_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Write the profile narrative for {len(reports)} session(s):\n\n{_session_payload(reports, decision_stats=decision_stats, episodes=episodes)}",
        },
    ]
    try:
        parsed = await parse_structured_completion(
            client,
            settings=settings,
            model=model,
            messages=messages,
            response_model=_LLMProfileNarrative,
        )
        if not parsed:
            return None
        return ProfileNarrative.model_validate(parsed.model_dump())
    except Exception:
        logger.exception("Profile narrative LLM generation failed")
        return None
