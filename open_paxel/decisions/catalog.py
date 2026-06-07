from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from open_paxel.config import project_root


class DecisionPattern(BaseModel):
    key: str
    title: str
    category: str
    pattern: str


def _catalog_paths() -> list[Path]:
    root = project_root()
    pkg_data = Path(__file__).resolve().parent.parent / "data" / "decision_catalog.json"
    return [
        root / "assets" / "decision_catalog.json",
        pkg_data,
        root / "decision_catalog.json",
    ]


@lru_cache
def load_decision_catalog() -> list[DecisionPattern]:
    for path in _catalog_paths():
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [DecisionPattern.model_validate(item) for item in raw]
    raise FileNotFoundError(
        "decision_catalog.json not found in assets/, open_paxel/data/, or project root"
    )


def catalog_by_key() -> dict[str, DecisionPattern]:
    return {p.key: p for p in load_decision_catalog()}


def compact_catalog_for_prompt(*, pattern_max_len: int = 180) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for p in load_decision_catalog():
        snippet = p.pattern if len(p.pattern) <= pattern_max_len else p.pattern[: pattern_max_len - 3] + "..."
        items.append(
            {"key": p.key, "title": p.title, "category": p.category, "pattern": snippet}
        )
    return items


def resolve_catalog_match(key: str | None) -> DecisionPattern | None:
    if not key:
        return None
    return catalog_by_key().get(key)
