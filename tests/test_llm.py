from open_paxel.config import Settings
from open_paxel.llm.client import create_async_llm_client
from open_paxel.llm.structured import _strip_json_fence
from open_paxel.scorer.registry import get_scorer


def test_ollama_llm_configured_without_api_key():
    settings = Settings(llm_provider="ollama", openai_api_key=None, dry_run=False)
    assert settings.llm_configured() is True


def test_openai_requires_api_key_for_llm_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(llm_provider="openai", openai_api_key=None, dry_run=False)
    assert settings.llm_configured() is False


def test_openrouter_requires_api_key_for_llm_configured(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = Settings(llm_provider="openrouter", openrouter_api_key=None, dry_run=False)
    assert settings.llm_configured() is False


def test_openrouter_llm_configured_with_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_PAXEL_OPENROUTER_API_KEY", raising=False)
    settings = Settings(
        llm_provider="openrouter",
        dry_run=False,
        **{"OPENROUTER_API_KEY": "sk-or-v1-test"},
    )
    assert settings.llm_configured() is True
    assert settings.resolve_api_key() == "sk-or-v1-test"


def test_create_openrouter_client(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_PAXEL_OPENROUTER_API_KEY", raising=False)
    settings = Settings(
        llm_provider="openrouter",
        openrouter_base_url="https://openrouter.ai/api/v1",
        dry_run=False,
        **{"OPENROUTER_API_KEY": "sk-or-v1-test"},
    )
    client = create_async_llm_client(settings)
    assert client is not None
    assert "openrouter.ai" in str(client.base_url)


def test_create_openrouter_client_requires_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = Settings(llm_provider="openrouter", openrouter_api_key=None, dry_run=False)
    assert create_async_llm_client(settings) is None


def test_effective_model_openrouter_default():
    settings = Settings(llm_provider="openrouter", model="", dry_run=False)
    assert settings.effective_model() == "openai/gpt-4o-mini"


def test_get_scorer_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_PAXEL_OPENROUTER_API_KEY", raising=False)
    scorer = get_scorer(
        Settings(
            llm_provider="openrouter",
            model="openai/gpt-4o-mini",
            dry_run=False,
            **{"OPENROUTER_API_KEY": "sk-or-v1-test"},
        )
    )
    assert scorer.model == "openai/gpt-4o-mini"


def test_create_ollama_client():
    settings = Settings(
        llm_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434",
        dry_run=False,
    )
    client = create_async_llm_client(settings)
    assert client is not None
    assert str(client.base_url).rstrip("/").endswith("/v1")


def test_create_openai_client_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(llm_provider="openai", openai_api_key=None, dry_run=False)
    assert create_async_llm_client(settings) is None


def test_strip_json_fence():
    raw = '```json\n{"name": "x", "score": 1.0}\n```'
    assert _strip_json_fence(raw) == '{"name": "x", "score": 1.0}'


def test_get_scorer_ollama():
    scorer = get_scorer(Settings(llm_provider="ollama", model="llama3.2", dry_run=False))
    assert scorer.model == "llama3.2"
