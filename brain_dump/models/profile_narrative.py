from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileNarrative(BaseModel):

    narrative: str = ""
    what_you_built: str = ""
    decision_patterns: str = ""
    matched_pattern: str | None = None
    matched_pattern_category: str | None = None
    strengths: list[str] = Field(default_factory=list)
    growth_areas: list[str] = Field(default_factory=list)
