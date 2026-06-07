from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_home() -> Path:
    return Path(os.environ.get("BRAIN_DUMP_HOME", Path.home() / ".brain-dump"))


@lru_cache
def project_root() -> Path:
    """Repo root (directory containing pyproject.toml)."""
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parent


def env_file_paths() -> list[Path]:
    """`.env` files to load (first → last; later files do not override existing vars)."""
    home = default_home()
    return [
        project_root() / ".env",
        home / ".env",
    ]


def load_env_files(*, override: bool = False) -> list[Path]:
    """Load dotenv files into os.environ. Returns paths that were loaded."""
    loaded: list[Path] = []
    for path in env_file_paths():
        if path.is_file():
            load_dotenv(path, override=override)
            loaded.append(path)
    return loaded


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BRAIN_DUMP_",
        extra="ignore",
    )

    home: Path = Field(default_factory=default_home)
    llm_provider: str = "openai"
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "BRAIN_DUMP_OPENAI_API_KEY"),
    )
    model: str = "gpt-4.1-mini"
    concurrency: int = 3
    redaction_level: str = "standard"
    dry_run: bool = False
    ephemeral_jobs: bool = False

    @property
    def db_path(self) -> Path:
        self.home.mkdir(parents=True, exist_ok=True)
        return self.home / "profile.db"

    @property
    def config_path(self) -> Path:
        return self.home / "config.toml"

    def resolve_api_key(self) -> str | None:
        return self.openai_api_key

    @classmethod
    def load(cls) -> Settings:
        # 1) .env (project, then ~/.brain-dump/) — does not override existing env vars
        load_env_files(override=False)

        # 2) ~/.brain-dump/config.toml as defaults
        home = default_home()
        config_file = home / "config.toml"
        toml_data: dict = {}
        if config_file.exists():
            toml_data.update(_parse_simple_toml(config_file.read_text(encoding="utf-8")))

        # 3) pydantic-settings reads os.environ (wins over toml kwargs)
        return cls(**toml_data)


def _parse_simple_toml(text: str) -> dict:
    """Minimal TOML parser for flat key = value config."""
    result: dict = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.isdigit():
            result[key] = int(value)
        elif value.lower() in ("true", "false"):
            result[key] = value.lower() == "true"
        else:
            result[key] = value
    return result


def write_default_config(home: Path, api_key: str) -> Path:
    home.mkdir(parents=True, exist_ok=True)
    path = home / "config.toml"
    if path.exists():
        return path
    path.write_text(
        f'''# Brain Dump configuration
llm_provider = "openai"
openai_api_key = "{api_key}"
model = "gpt-4.1-mini"
concurrency = 3
redaction_level = "standard"
''',
        encoding="utf-8",
    )
    return path
