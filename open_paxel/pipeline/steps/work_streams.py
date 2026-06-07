from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from open_paxel.models.domain import SessionReport
from open_paxel.models.pipeline_models import WorkStream


def build_work_streams(
    reports: list[SessionReport],
    *,
    gap_hours: int = 48,
) -> list[WorkStream]:
    by_project: dict[str, list[SessionReport]] = {}
    for report in reports:
        key = report.project_path or "unknown"
        by_project.setdefault(key, []).append(report)

    streams: list[WorkStream] = []
    gap = timedelta(hours=gap_hours)

    for project_path, project_reports in by_project.items():
        ordered = sorted(
            project_reports,
            key=lambda r: r.started_at or r.analyzed_at,
        )
        batch: list[SessionReport] = []
        prev_end: datetime | None = None

        def flush() -> None:
            if not batch:
                return
            started = batch[0].started_at or batch[0].analyzed_at
            ended = batch[-1].ended_at or batch[-1].analyzed_at
            streams.append(
                WorkStream(
                    id=str(uuid.uuid4()),
                    project_path=project_path,
                    session_ids=[r.session_id for r in batch],
                    started_at=started,
                    ended_at=ended,
                )
            )

        for report in ordered:
            start = report.started_at or report.analyzed_at
            if prev_end and start and (start - prev_end) > gap and batch:
                flush()
                batch = []
            batch.append(report)
            prev_end = report.ended_at or report.analyzed_at or start
        flush()

    return streams
