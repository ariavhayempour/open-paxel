from __future__ import annotations

from brain_dump.config import Settings
from brain_dump.scorer.openai_scorer import OpenAIScorer


def get_scorer(settings: Settings):
    if settings.llm_provider == "openai":
        key = settings.resolve_api_key()
        if not key and not settings.dry_run:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY or openai_api_key in config.toml"
            )
        return OpenAIScorer(api_key=key or "dry-run", model=settings.model, dry_run=settings.dry_run)
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")
