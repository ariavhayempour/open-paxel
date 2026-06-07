from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    score: float
    narrative: str = ""
    evidence: list[str] = Field(default_factory=list)
