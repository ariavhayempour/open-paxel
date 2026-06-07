# Brain Dump

Local-first [Paxel](https://paxel.ycombinator.com/)-style analyzer for **Claude Code** sessions. Builds a historical builder profile across five dimensions — steering, execution, engineering, product instinct, and planning — with insight cards and a neobrutalism dashboard.

**Privacy:** transcripts stay on your machine. Only redacted excerpts go to **your OpenAI API key**. Scores are stored locally in SQLite.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — creates and manages the Python virtualenv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows: irm https://astral.sh/uv/install.ps1 | iex
```

## Quick start

```bash
uv sync --all-groups          # creates .venv + installs deps

# OpenAI key — pick one:
#   .env in project root (recommended): OPENAI_API_KEY=sk-...
#   export OPENAI_API_KEY=sk-...
#   uv run brain-dump init-config

cp .env.example .env          # then edit .env

uv run brain-dump discover
uv run brain-dump upload -y
uv run brain-dump profile --open   # http://127.0.0.1:3847
```

Or run the installer:

```bash
./install.sh      # Git Bash / macOS / Linux
./install.ps1     # Windows PowerShell
```

Both scripts run `uv sync --all-groups` only (uv required; no pip fallback).

## Commands

Use `uv run` so you always execute inside the project `.venv`:

| Command | Description |
|---------|-------------|
| `uv run brain-dump discover` | List Claude Code repos + session counts |
| `uv run brain-dump upload` | Batch analyze sessions |
| `uv run brain-dump analyze <file.jsonl>` | Analyze one session |
| `uv run brain-dump profile` | Show builder profile |
| `uv run brain-dump serve` | Run FastAPI + dashboard |
| `uv run pytest` | Run tests |

## Development

**Single runner (backend + frontend):**

```bash
uv run python dev.py
uv run python dev.py --open    # also opens http://localhost:5173
# or:
uv run brain-dump dev --open
```

**Or run separately:**

```bash
uv sync --all-groups
uv run pytest
uv run ruff check brain_dump
uv run brain-dump serve

cd frontend && npm install && npm run dev
npm run build    # → brain_dump/static/
```

## Claude Code plugin

Install the CLI globally so SessionEnd hooks find `brain-dump`:

```bash
uv tool install -e .
claude --plugin-dir ./plugin
```

Skills: `/session-profile:analyze`, `/session-profile:profile`, `/session-profile:upload`

## Config

**Credential priority** (highest first):

1. Shell environment (`OPENAI_API_KEY`, `BRAIN_DUMP_*`)
2. [`.env`](.env) in project root (see [`.env.example`](.env.example))
3. `~/.brain-dump/.env`
4. `~/.brain-dump/config.toml`

```toml
# ~/.brain-dump/config.toml
llm_provider = "openai"
openai_api_key = "sk-..."
model = "gpt-4.1-mini"
concurrency = 3
```

Supported in `.env`:

```env
OPENAI_API_KEY=sk-...
BRAIN_DUMP_MODEL=gpt-4.1-mini
BRAIN_DUMP_LLM_PROVIDER=openai
BRAIN_DUMP_HOME=
BRAIN_DUMP_CONCURRENCY=3
```

## License

MIT
