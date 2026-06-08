from __future__ import annotations

from open_paxel.config import Settings
from open_paxel.scorer.openai_scorer import OpenAIScorer


def get_scorer(settings: Settings):
    provider = settings.llm_provider.lower()
    if provider == "openai":
        key = settings.resolve_api_key()
        if not key and not settings.dry_run:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY or openai_api_key in config.toml"
            )
        return OpenAIScorer(settings)
    if provider == "ollama":
        return OpenAIScorer(settings)
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}. Use 'openai' or 'ollama'.")
