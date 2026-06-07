from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from brain_dump.config import Settings, write_default_config
from brain_dump.db.repository import SQLiteRepository
from brain_dump.discover.scanner import discover_repos, filter_repos_by_cwd
from brain_dump.pipeline import AnalysisPipeline

app = typer.Typer(
    name="brain-dump",
    help="Analyze Claude Code sessions and build your local builder profile.",
    no_args_is_help=True,
)
console = Console()


def _settings(dry_run: bool = False) -> Settings:
    s = Settings.load()
    if dry_run:
        s.dry_run = True
    return s


def _repo(settings: Settings) -> SQLiteRepository:
    settings.home.mkdir(parents=True, exist_ok=True)
    return SQLiteRepository(settings.db_path)


def _pipeline(settings: Settings) -> AnalysisPipeline:
    return AnalysisPipeline(settings, _repo(settings))


@app.command()
def discover(
    cwd: bool = typer.Option(False, "--cwd", help="Only repos under current directory"),
):
    """List Claude Code repos and session counts."""
    repos = discover_repos()
    if cwd:
        repos = filter_repos_by_cwd(repos, Path.cwd())
    table = Table(title="Claude Code Repositories")
    table.add_column("Name")
    table.add_column("Path")
    table.add_column("Sessions", justify="right")
    for r in repos:
        table.add_row(r.name, r.path, str(r.session_count))
    console.print(table)
    console.print(f"\nTotal: {len(repos)} repos, {sum(r.session_count for r in repos)} sessions")


@app.command()
def analyze(
    path: Path | None = typer.Argument(None, help="Path to .jsonl transcript"),
    latest: bool = typer.Option(False, "--latest", help="Analyze latest session for cwd project"),
    async_run: bool = typer.Option(False, "--async", help="Fire and forget (for hooks)"),
    transcript_from_stdin: bool = typer.Option(
        False, "--transcript-from-stdin", help="Read SessionEnd hook JSON from stdin"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip LLM call and DB write"),
    force: bool = typer.Option(False, "--force", help="Re-analyze even if cached"),
):
    """Analyze a single Claude Code session."""
    settings = _settings(dry_run=dry_run)
    if force:
        settings.dry_run = dry_run  # force handled in pipeline via re-parse

    if transcript_from_stdin:
        raw = sys.stdin.read()
        data = json.loads(raw)
        path = Path(data["transcript_path"])

    if latest and path is None:
        repos = filter_repos_by_cwd(discover_repos(), Path.cwd())
        if not repos:
            console.print("[red]No sessions found for current project[/red]")
            raise typer.Exit(1)
        sessions = sorted(repos[0].session_paths, key=lambda p: p.stat().st_mtime, reverse=True)
        path = sessions[0]

    if path is None:
        console.print("[red]Provide a path, --latest, or --transcript-from-stdin[/red]")
        raise typer.Exit(1)

    async def run():
        pipeline = _pipeline(settings)
        report = await pipeline.analyze_file(path, force=force)
        console.print(f"[green]Analyzed[/green] {report.session_id}: {report.title or 'Untitled'}")
        for dim, score in report.dimensions.items():
            console.print(f"  {dim}: {score.score}")

    if async_run:
        subprocess.Popen(
            [sys.executable, "-m", "brain_dump.cli", "analyze", str(path)]
            + (["--force"] if force else [])
            + (["--dry-run"] if dry_run else []),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return
    else:
        asyncio.run(run())


@app.command()
def upload(
    project: str | None = typer.Option(None, "--project", help="Filter repo by name"),
    force: bool = typer.Option(False, "--force"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation"),
):
    """Batch-analyze sessions (Paxel-style upload)."""
    settings = _settings(dry_run=dry_run)
    repos = discover_repos()
    repos = filter_repos_by_cwd(repos, Path.cwd()) or repos
    if project:
        repos = [r for r in repos if project.lower() in r.name.lower()]

    if not repos:
        console.print("[red]No repositories found under ~/.claude/projects[/red]")
        raise typer.Exit(1)

    console.print("Repositories to analyze:")
    for i, r in enumerate(repos, 1):
        console.print(f"  [{i}] {r.name} ({r.session_count} sessions) — {r.path}")

    if not yes:
        selected = typer.prompt("Enter numbers comma-separated (or 'all')", default="all")
    else:
        selected = "all"

    if selected.strip().lower() == "all":
        chosen = repos
    else:
        indices = [int(x.strip()) - 1 for x in selected.split(",") if x.strip()]
        chosen = [repos[i] for i in indices if 0 <= i < len(repos)]

    paths: list[Path] = []
    project_paths: list[str] = []
    for r in chosen:
        project_paths.append(r.path)
        for p in r.session_paths:
            if not force and _repo(settings).report_exists(p.stem):
                continue
            paths.append(p)

    if not paths:
        console.print("[yellow]All sessions already analyzed. Use --force to re-run.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Analyzing {len(paths)} session(s)...")

    async def batch():
        pipeline = _pipeline(settings)
        sem = asyncio.Semaphore(settings.concurrency)
        results = []

        async def one(p: Path):
            async with sem:
                try:
                    return await pipeline.analyze_file(p, force=force)
                except Exception as e:
                    console.print(f"[red]Failed {p.name}: {e}[/red]")
                    return None

        results = await asyncio.gather(*[one(p) for p in paths])
        ok = [r for r in results if r]
        if ok and not dry_run:
            upload = _repo(settings).create_upload(
                [r.session_id for r in ok],
                project_paths,
            )
            console.print(f"[green]Upload complete[/green] id={upload.id} sessions={len(ok)}")
        console.print(f"Done: {len(ok)}/{len(paths)} sessions")

    asyncio.run(batch())


@app.command()
def profile(
    fmt: str = typer.Option("text", "--format", help="text|json|md"),
    open_browser: bool = typer.Option(False, "--open", help="Start server and open dashboard"),
):
    """Show aggregated builder profile."""
    settings = Settings.load()
    if open_browser:
        serve(port=3847, open_browser=True)
        return

    p = _repo(settings).get_profile()
    if fmt == "json":
        console.print(p.model_dump_json(indent=2))
        return
    if fmt == "md":
        lines = [
            f"# Builder Profile — {p.archetype}",
            "",
            f"Sessions: {p.session_count} | Uploads: {p.upload_count}",
            "",
            "## Dimensions",
        ]
        for d, s in p.dimensions.items():
            lines.append(f"- **{d}**: {s}")
        lines.append("\n## Growth edge")
        for g in p.growth_edge:
            lines.append(f"- {g}")
        console.print("\n".join(lines))
        return

    console.print(f"\n[bold]Archetype:[/bold] {p.archetype}")
    console.print(f"Sessions: {p.session_count}\n")
    for card in p.insight_cards:
        sub = f" ({card.subtitle})" if card.subtitle else ""
        console.print(f"  • {card.title}: [cyan]{card.value}[/cyan]{sub}")
    console.print("\n[bold]Dimensions[/bold]")
    for d, s in p.dimensions.items():
        console.print(f"  {d}: {s}")


@app.command("list")
def list_sessions(limit: int = 20):
    """List analyzed sessions."""
    reports = _repo(Settings.load()).list_reports(limit=limit)
    for r in reports:
        console.print(f"{r.analyzed_at.date()}  {r.session_id[:8]}…  {r.title or 'Untitled'}")


@app.command()
def dev(
    backend_port: int = typer.Option(3847, "--backend-port"),
    frontend_port: int = typer.Option(5173, "--frontend-port"),
    open_browser: bool = typer.Option(False, "--open"),
    backend_only: bool = typer.Option(False, "--backend-only"),
):
    """Run backend + frontend dev servers together."""
    from brain_dump.dev_runner import run_dev

    run_dev(
        backend_port=backend_port,
        frontend_port=frontend_port,
        open_browser=open_browser,
        backend_only=backend_only,
    )


@app.command()
def serve(
    port: int = typer.Option(3847, "--port"),
    open_browser: bool = typer.Option(False, "--open"),
    log_level: str = typer.Option("INFO", "--log-level", help="DEBUG, INFO, WARNING"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Reload on code changes"),
):
    """Run FastAPI dashboard server."""
    from brain_dump.api.app import create_app
    from brain_dump.logging_config import setup_logging

    setup_logging(log_level)

    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}")
    uvicorn.run(
        "brain_dump.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=port,
        reload=reload,
        log_level="info",
    )


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete all analyzed sessions, uploads, jobs, and temp files. Keeps config.toml."""
    settings = Settings.load()
    home = settings.home

    if not yes:
        typer.confirm(
            f"This will erase all data in {home} (sessions, profile, jobs). Continue?",
            abort=True,
        )

    from brain_dump.reset import reset_brain_dump_data

    reset_brain_dump_data(settings)
    console.print(
        f"[green]Brain Dump data reset.[/green] Config kept at {home / 'config.toml'}\n"
        "Restart the server if it is running so it picks up the clean state."
    )


@app.command()
def init_config(
    api_key: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Create ~/.brain-dump/config.toml with your OpenAI API key."""
    home = Settings.load().home
    path = write_default_config(home, api_key)
    console.print(f"[green]Config written to[/green] {path}")


def main():
    app()


if __name__ == "__main__":
    main()
