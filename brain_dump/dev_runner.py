"""Start Brain Dump backend (FastAPI) and frontend (Vite) together."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

procs: list[subprocess.Popen] = []


def _which(name: str) -> str | None:
    return shutil.which(name)


def _stop_all() -> None:
    for p in procs:
        if p.poll() is None:
            p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    procs.clear()


def _handle_signal(signum, frame) -> None:
    _stop_all()
    sys.exit(0)


def _popen(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> subprocess.Popen:
    kwargs: dict = {
        "cwd": cwd or ROOT,
        "env": env or os.environ.copy(),
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def run_dev(
    *,
    backend_port: int = 3847,
    frontend_port: int = 5173,
    open_browser: bool = False,
    frontend_only: bool = False,
    backend_only: bool = False,
) -> None:
    if backend_only and frontend_only:
        print("Cannot pass both backend_only and frontend_only.", file=sys.stderr)
        sys.exit(1)

    if not backend_only:
        if not _which("npm"):
            print("npm is required for the frontend. Install Node.js or use --backend-only.", file=sys.stderr)
            sys.exit(1)
        if not (FRONTEND / "package.json").exists():
            print(f"Frontend not found at {FRONTEND}", file=sys.stderr)
            sys.exit(1)
        if not (FRONTEND / "node_modules").exists():
            print("Installing frontend dependencies (npm install)…")
            subprocess.run(["npm", "install"], cwd=FRONTEND, check=True)

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    if not frontend_only:
        backend_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "brain_dump.api.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(backend_port),
            "--log-level",
            "info",
        ]
        print(f"Starting backend  → http://127.0.0.1:{backend_port}")
        procs.append(_popen(backend_cmd))

    if not backend_only:
        frontend_cmd = [
            "npm",
            "run",
            "dev",
            "--",
            "--port",
            str(frontend_port),
            "--strictPort",
        ]
        print(f"Starting frontend → http://127.0.0.1:{frontend_port}")
        procs.append(_popen(frontend_cmd, cwd=FRONTEND))

    time.sleep(1.5)

    for p in procs:
        if p.poll() is not None:
            print("A dev server exited early. Check logs above.", file=sys.stderr)
            _stop_all()
            sys.exit(p.returncode or 1)

    if open_browser:
        if backend_only:
            webbrowser.open(f"http://127.0.0.1:{backend_port}")
        else:
            webbrowser.open(f"http://127.0.0.1:{frontend_port}")

    print("\nPress Ctrl+C to stop all servers.\n")

    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    print("A dev server stopped unexpectedly.", file=sys.stderr)
                    _stop_all()
                    sys.exit(p.returncode or 1)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _stop_all()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Brain Dump backend + frontend dev servers")
    parser.add_argument("--backend-port", type=int, default=3847)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--open", action="store_true", help="Open dashboard in browser")
    parser.add_argument("--backend-only", action="store_true", help="Backend only")
    parser.add_argument("--frontend-only", action="store_true", help="Frontend only (API must be running)")
    args = parser.parse_args()
    run_dev(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        open_browser=args.open,
        backend_only=args.backend_only,
        frontend_only=args.frontend_only,
    )


if __name__ == "__main__":
    main()
