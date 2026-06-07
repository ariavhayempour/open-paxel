#!/usr/bin/env python3
"""Start Brain Dump backend (FastAPI) and frontend (Vite) together.

Usage:
    uv run python dev.py
    uv run python dev.py --open
"""

from brain_dump.dev_runner import main

if __name__ == "__main__":
    main()
