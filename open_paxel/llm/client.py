from __future__ import annotations

from openai import AsyncOpenAI

from open_paxel.config import Settings

OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434/v1"


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

    if provider == "ollama":
        base_url = settings.ollama_base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return AsyncOpenAI(base_url=base_url, api_key="ollama")

    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")


def llm_provider_label(settings: Settings) -> str:
    if settings.llm_provider.lower() == "ollama":
        return "Ollama"
    return "OpenAI"
