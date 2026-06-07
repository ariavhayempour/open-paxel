from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brain_dump.parser.claude_jsonl import decode_project_path


@dataclass
class RepoInfo:
    name: str
    path: str
    encoded_dir: str
    session_count: int
    session_paths: list[Path]


def find_claude_projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def discover_repos(projects_root: Path | None = None) -> list[RepoInfo]:
    root = projects_root or find_claude_projects_root()
    if not root.exists():
        return []

    repos: list[RepoInfo] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        sessions = [
            p
            for p in entry.glob("*.jsonl")
            if p.is_file() and not p.name.startswith(".")
        ]
        if not sessions:
            continue
        decoded = decode_project_path(entry.name)
        name = Path(decoded).name or entry.name
        repos.append(
            RepoInfo(
                name=name,
                path=decoded,
                encoded_dir=entry.name,
                session_count=len(sessions),
                session_paths=sessions,
            )
        )
    return repos


def filter_repos_by_cwd(repos: list[RepoInfo], cwd: Path) -> list[RepoInfo]:
    cwd_str = str(cwd.resolve()).lower().replace("/", "\\")
    return [r for r in repos if r.path.lower().replace("/", "\\").startswith(cwd_str)]
