from __future__ import annotations

from openai import AsyncOpenAI

from open_paxel.config import Settings

OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def _normalize_v1_base_url(url: str) -> str:
    base_url = url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return base_url


def create_async_llm_client(settings: Settings) -> AsyncOpenAI | None:
    """Return an OpenAI-compatible async client for the configured provider."""
    if settings.dry_run:
        return None

    provider = settings.llm_provider.lower()
    if provider == "openai":
        key = settings.resolve_api_key()
        if not key:
            return None
        return AsyncOpenAI(api_key=key)

    if provider == "openrouter":
        key = settings.resolve_api_key()
        if not key:
            return None
        return AsyncOpenAI(
            base_url=_normalize_v1_base_url(settings.openrouter_base_url),
            api_key=key,
        )

    if provider == "ollama":
        return AsyncOpenAI(
            base_url=_normalize_v1_base_url(settings.ollama_base_url),
            api_key="ollama",
        )

    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")


def llm_provider_label(settings: Settings) -> str:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return "Ollama"
    if provider == "openrouter":
        return "OpenRouter"
    return "OpenAI"
