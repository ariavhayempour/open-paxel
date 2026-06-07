from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["sessions"])


class UpdateSessionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.get("/sessions")
def list_sessions(request: Request, limit: int = 50, offset: int = 0):
    repo = request.app.state.repository
    reports = repo.list_reports(limit=limit, offset=offset)
    return {
        "items": [
            {
                "session_id": r.session_id,
                "title": r.title,
                "project_path": r.project_path,
                "analyzed_at": r.analyzed_at,
                "archetype": r.archetype,
                "dimensions": {k: v.score for k, v in r.dimensions.items()},
            }
            for r in reports
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: str, request: Request):
    repo = request.app.state.repository
    report = repo.get_report(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    return report


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: UpdateSessionRequest, request: Request):
    repo = request.app.state.repository
    report = repo.update_report_title(session_id, body.title)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    return report
