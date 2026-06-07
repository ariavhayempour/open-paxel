from __future__ import annotations

from pathlib import Path
from typing import Protocol

from open_paxel.models.domain import (
    BuilderProfile,
    HeuristicMetrics,
    RedactedExcerpt,
    SessionFacts,
    SessionReport,
    SessionScore,
    UploadReport,
)


class TranscriptParser(Protocol):
    def parse(self, path: Path) -> SessionFacts: ...


class LLMScorer(Protocol):
    async def score_session(
        self,
        facts: SessionFacts,
        metrics: HeuristicMetrics,
        excerpts: RedactedExcerpt,
    ) -> SessionScore: ...


class ReportRepository(Protocol):
    def save_report(self, report: SessionReport) -> None: ...

    def get_report(self, session_id: str) -> SessionReport | None: ...

    def list_reports(self, limit: int = 100, offset: int = 0) -> list[SessionReport]: ...

    def report_exists(self, session_id: str) -> bool: ...

    def create_upload(self, session_ids: list[str], project_paths: list[str]) -> UploadReport: ...

    def get_upload(self, upload_id: str) -> UploadReport | None: ...

    def list_uploads(self) -> list[UploadReport]: ...

    def get_profile(self) -> BuilderProfile: ...
