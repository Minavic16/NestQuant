"""Structured logging configuration."""
from __future__ import annotations

import logging
import sys

from nestquant.core.configuration.runtime import get_runtime


def configure_logging(level: str | None = None) -> None:
    rt = get_runtime()
    lvl = (level or rt.log_level).upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        if rt.json_logs
        else "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )


def logger_adapter(name: str) -> logging.Logger:
    return logging.getLogger(name)
