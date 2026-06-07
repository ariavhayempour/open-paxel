# AGENTS.md — Open-Paxel

Guidance for AI coding agents working in this repository.

## Project summary

**Open-Paxel** is a local-first, open [Paxel](https://paxel.ycombinator.com/)-style analyzer for **Claude Code** sessions. It builds a historical **builder profile** (five dimensions + narrative + decision patterns) from session transcripts. Data stays on the user's machine; only redacted excerpts are sent to **their OpenAI API key**.

| Surface | Name |
|---------|------|
| User-facing product | **Open-Paxel** |
| CLI command | `open-paxel` |
| Python package (internal) | `open_paxel` |
| PyPI / uv project name | `open-paxel` |
| Data directory (default) | `~/.open-paxel/` (legacy: `~/.brain-dump/`) |

---

## Architecture

```
CLI (cli.py) ──────────────┐
API (api/routes/*) ────────┼──► upload/worker.py
                           │         │
                           │         ▼
                           │    AnalysisPipeline (pipeline/analysis.py)  ← per session
                           │         │
                           │         ▼
                           └──► PaxelPipeline (pipeline/orchestrator.py)  ← batch after upload
                                     │
                                     ▼
                              assemble_profile (profile/assembler.py)
                                     │
                                     ▼
                              SQLiteRepository (~/.open-paxel/profile.db)
                                     │
                                     ▼
                              FastAPI + React dashboard
```

### Key modules

| Area | Path | Responsibility |
|------|------|----------------|
| Discovery | `open_paxel/discover/scanner.py` | Match CWD → Claude project in `~/.claude/projects/` |
| Parsers | `open_paxel/parser/` | `.jsonl` (Claude), `.md`/`.txt` (text + frontmatter) |
| Per-session pipeline | `open_paxel/pipeline/analysis.py` | Parse → heuristics → LLM narrative/scores → save report |
| Batch pipeline | `open_paxel/pipeline/orchestrator.py` | Git, work streams, decisions, episodes, profile |
| Decisions | `open_paxel/decisions/`, `assets/decision_catalog.json` | 49-pattern catalog + LLM classifier |
| Profile | `open_paxel/profile/` | Aggregate, heuristic narrative, LLM enrich |
| Git | `open_paxel/git/reader.py` | Log read, commit↔session linking, code-quality label |
| DB | `open_paxel/db/` | SQLAlchemy models + `SQLiteRepository` |
| Frontend | `frontend/src/` | React 19 + Vite; build → `open_paxel/static/` |
| Config | `open_paxel/config.py` | Settings, `OPEN_PAXEL_*` env vars, legacy `BRAIN_DUMP_*` |

### Pipeline order (batch)

1. Discover project path  
2. Read git history  
3. Link commits to sessions (requires `started_at`/`ended_at`)  
4. Group work streams  
5. Steering traces (on reports from per-session step)  
6. Classify decisions (LLM)  
7. Redact decisions  
8. Link decision outcomes + catalog match  
9. Code quality label  
10. Score episodes (LLM)  
11. Assemble profile  

---

## User workflows (what the product does)

### CLI (full git + discovery)

Run from the **user's project directory**, not the Open-Paxel repo:

```powershell
open-paxel discover
open-paxel upload -y
open-paxel profile --open
```

`discover` is **CWD-only**. It matches Claude's encoded folder names (e.g. `Z--June-26-audiobook-generator`) via path normalization **and** encoded-key fingerprinting (spaces/underscores vs hyphens).

### Dashboard

- `open-paxel serve` → http://127.0.0.1:3847  
- `open-paxel dev --open` → backend + Vite (5173)  
- Uploads page accepts `.jsonl`, `.md`, `.txt` (background jobs via `upload/worker.py`)

**UI uploads do not call CWD discovery.** Git integration for text files requires YAML frontmatter `project:` or `cwd:`. Commit linking for text still needs session timestamps (not yet parsed from frontmatter).

---

## Development commands

```bash
uv sync --all-groups
uv run pytest
uv run ruff check open_paxel
uv run open-paxel dev --open

# Production frontend build (served by FastAPI)
cd frontend && npm install && npm run build
```

Global CLI install (for testing outside repo):

```bash
uv tool install --editable .
```

---

## Coding conventions

1. **Minimize scope** — smallest correct diff; match existing style in surrounding files.
2. **Avoid circular imports** — known cycle: `aggregate` ↔ `pipeline` ↔ `assembler` ↔ `enrich`. Use:
   - `TYPE_CHECKING` imports in type hints
   - Lazy imports inside functions
   - `pipeline/__init__.py` lazy `PaxelPipeline` via `__getattr__`
   - Decision helpers live in `open_paxel/decisions/stats.py`, not re-exported through pipeline-only paths
3. **Lazy pipeline exports** — do not import `PaxelPipeline` at module level in `profile/` or `aggregate.py`.
4. **Privacy** — never log or persist raw API keys; redact before LLM calls (`open_paxel/redact/`).
5. **Local-first** — no cloud upload of full transcripts; SQLite is source of truth.
6. **Tests** — run `uv run pytest` after pipeline, discovery, parser, or API changes. Add focused tests in `tests/`.
7. **No drive-by refactors** — don't rename `open_paxel` package or move directories without explicit request.

---

## Common agent tasks

| Task | Where to work |
|------|----------------|
| Fix session discovery | `discover/scanner.py`, `parser/claude_jsonl.py` (`decode_project_path`) |
| Add parser support | `parser/auto.py`, `parser/text_session.py` or `claude_jsonl.py` |
| Change LLM prompts/scoring | `scorer/session_narrative.py`, `decision_classifier.py`, `episode_scorer.py`, `profile/narrative_llm.py` |
| Add pipeline step | `pipeline/orchestrator.py`, new module under `pipeline/steps/` |
| Extend profile UI | `frontend/src/pages/ProfilePage.tsx`, `lib/api.ts` |
| New API endpoint | `open_paxel/api/routes/`, register in `api/app.py` |
| Decision patterns | `assets/decision_catalog.json` + `decisions/catalog.py` |
| Config / env vars | `config.py`, `.env.example`, README.md |

---

## Discovery pitfalls (read before editing scanner)

Claude encodes paths as folder names like `Z--June-26-audiobook-generator`. Naive decode (`-` → `\`) produces wrong paths (`Z:\June\26\audiobook\generator` vs real `Z:\June 26\audiobook_generator`).

**Always use both:**

- Path prefix matching (with `_` → nested path aliases, user-home false-positive filter)
- `_claude_encoded_key()` fingerprint match against `repo.encoded_dir`

When fingerprint matches but decode is wrong, correct `RepoInfo.path` to the actual CWD via `_correct_repo_path()`.

Do **not** use `Path.resolve()` on malformed paths before fixing them — relative resolution causes false matches (e.g. `c//Users/...` resolving under open_paxel repo).

---

## Git integration rules

| Source | `project_path` | Timestamps | Git commits linked? |
|--------|----------------|------------|---------------------|
| CLI `upload` | CWD discovery | From JSONL | Yes |
| UI `.jsonl` | From transcript `cwd` | From JSONL | Yes |
| UI `.md`/`.txt` | Frontmatter `project:`/`cwd:` only | Not parsed yet | No (log may still run) |

CLI upload passes `repo_info` into `PipelineContext`; UI worker passes `repo_info=None`.

---

## Testing checklist

After changes, verify:

- [ ] `uv run pytest` passes  
- [ ] Discovery tests in `tests/test_paxel_pipeline.py` if scanner touched  
- [ ] Parser tests in `tests/test_parser.py`, `tests/test_text_parser.py` if parsers touched  
- [ ] API upload tests in `tests/test_api_upload.py` if worker/API touched  
- [ ] No new circular import on `from open_paxel.profile.aggregate import build_profile`  

---

## Files agents should not commit unless asked

- `.env` (secrets)
- `open_paxel/static/` (built assets — rebuild with `npm run build`)
- User data under `~/.open-paxel/` or `~/.brain-dump/`

---

## Documentation to keep in sync

When changing user-visible behavior, update:

- `README.md` — install, commands, workflows  
- `AGENTS.md` — this file  
- `.env.example` — env var names  
- Plugin skills under `plugin/skills/` if CLI commands change  

---

## Product goals (for prioritization)

1. **Paxel parity** — local pipeline: narrative, builder map, decisions, episodes, git-aware profile.  
2. **Accurate discovery** — CWD → Claude sessions across Windows path quirks.  
3. **Privacy** — local transcripts, redacted LLM input, user's own API key.  
4. **Dual entry** — CLI for power users (full git); UI for drag-and-drop uploads.  

When unsure between a large refactor and a targeted fix, prefer the targeted fix.
