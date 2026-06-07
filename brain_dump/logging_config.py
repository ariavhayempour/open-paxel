from __future__ import annotations

import logging
import os
import sys


def setup_logging(level: str | None = None) -> None:
    """Configure brain_dump logging to stderr."""
    log_level = (level or os.environ.get("BRAIN_DUMP_LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, log_level, logging.INFO)

    root = logging.getLogger("brain_dump")
    if root.handlers:
        root.setLevel(numeric)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(numeric)
    root.propagate = False
