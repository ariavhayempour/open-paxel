#!/usr/bin/env python3
"""Start Open-Paxel backend (FastAPI) and frontend (Vite) together.

Usage:
    uv run python dev.py
    uv run python dev.py --open
"""

from open_paxel.dev_runner import main

if __name__ == "__main__":
    main()
