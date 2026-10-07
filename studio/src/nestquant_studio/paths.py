"""Filesystem locations for Studio, overridable by environment.

Nothing in Studio should hardcode a machine path. Resolution order:

* data:    $STUDIO_DATA_DIR, else $NQTS_DATA_DIR, else ./data
* logs:    $STUDIO_LOG_DIR,  else ./logs
* output:  $STUDIO_OUTPUT_DIR, else ./research/output  (experiment results)
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_path(*names: str, default: Path) -> Path:
    for n in names:
        v = os.getenv(n)
        if v:
            return Path(v).expanduser()
    return default


def data_dir() -> Path:
    return _env_path("STUDIO_DATA_DIR", "NQTS_DATA_DIR", default=Path.cwd() / "data")


def logs_dir() -> Path:
    return _env_path("STUDIO_LOG_DIR", default=Path.cwd() / "logs")


def output_dir() -> Path:
    return _env_path("STUDIO_OUTPUT_DIR", default=Path.cwd() / "research" / "output")


def has_market_data(sample: str = "EUR_USD.pkl") -> bool:
    """True when the market-data pickles needed by data-driven research exist."""
    return (data_dir() / sample).exists()
