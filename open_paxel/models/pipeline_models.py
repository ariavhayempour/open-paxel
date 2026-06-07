from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from open_paxel.models.scores import DimensionScore


class SessionNarrative(BaseModel):
    summary: str = ""
    what_was_built: str = ""
    technologies: list[str] = Field(default_factory=list)
    shipped: bool = False


class SteeringTrace(BaseModel):
    session_id: str
    text: str
    timestamp: datetime | None = None
    after_tool: bool = False


class Decision(BaseModel):
    session_id: str
    exchange_type: str = "strategic_redirect"
    catalog_key: str | None = None
    catalog_title: str | None = None
    catalog_category: str | None = None
    summary: str = ""
    evidence_quote: str = ""
    outcome_link: str | None = None


class GitCommit(BaseModel):
    hash: str
    message: str
    committed_at: datetime
    project_path: str


class WorkStream(BaseModel):
    id: str
    project_path: str
    session_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    git_commit_ids: list[str] = Field(default_factory=list)


class Episode(BaseModel):
    id: str
    work_stream_id: str
    title: str = ""
    session_ids: list[str] = Field(default_factory=list)
    dimensions: dict[str, DimensionScore] = Field(default_factory=dict)
    narrative: str = ""
    skipped: bool = False
    skip_reason: str | None = None


class PipelineArtifacts(BaseModel):
    project_path: str | None = None
    git_commits: list[GitCommit] = Field(default_factory=list)
    work_streams: list[WorkStream] = Field(default_factory=list)
    episodes: list[Episode] = Field(default_factory=list)
    code_quality_label: str | None = None
    decisions: list[Decision] = Field(default_factory=list)
