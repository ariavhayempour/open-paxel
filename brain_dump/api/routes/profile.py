from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["profile"])


@router.get("/profile")
def get_profile(request: Request):
    repo = request.app.state.repository
    return repo.get_profile()


@router.get("/profile/dimensions")
def get_dimensions(request: Request):
    profile = request.app.state.repository.get_profile()
    return {"dimensions": profile.dimensions, "updated_at": profile.updated_at}
