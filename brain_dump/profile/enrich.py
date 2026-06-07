from __future__ import annotations

from brain_dump.config import Settings
from brain_dump.db.repository import SQLiteRepository
from brain_dump.profile.aggregate import build_profile
from brain_dump.profile.narrative_llm import generate_profile_narrative_llm


async def enrich_profile_narrative(settings: Settings, repo: SQLiteRepository) -> bool:
    reports = repo.list_reports(limit=10_000)
    uploads = repo.list_uploads()
    profile = build_profile(reports, uploads)

    llm_narrative = await generate_profile_narrative_llm(reports, settings)
    if llm_narrative:
        profile = profile.model_copy(update={"narrative": llm_narrative})

    repo.save_profile_cache(profile)
    return llm_narrative is not None
