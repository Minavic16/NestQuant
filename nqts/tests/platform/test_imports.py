"""Smoke test: every module in the `nestquant` package must import cleanly.

Modules are discovered from the real package tree, so the test cannot drift out
of date when code moves. A module may only fail to import because an *optional
external* dependency is absent (e.g. MetaTrader5 on non-Windows); anything else
-- a SyntaxError, a broken internal import -- is a real failure.
"""
import importlib
from pathlib import Path

import pytest

import nestquant

OPTIONAL_EXTERNAL = {"MetaTrader5", "torch", "telegram", "pytz", "dotenv", "yaml", "flask", "httpx", "requests", "aiohttp"}


def _discover():
    """Walk the filesystem: `production/` is a namespace package (no __init__.py),
    which pkgutil.walk_packages would silently skip."""
    root = Path(nestquant.__file__).resolve().parent
    names = {"nestquant"}
    for py in root.rglob("*.py"):
        rel = py.relative_to(root).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts.pop()
        if not parts or "__pycache__" in parts:
            continue
        names.add(".".join(["nestquant", *parts]))
    return sorted(names)


@pytest.mark.parametrize("module", _discover())
def test_module_imports(module):
    try:
        importlib.import_module(module)
    except ModuleNotFoundError as e:
        missing = (e.name or "").split(".")[0]
        if missing in OPTIONAL_EXTERNAL:
            pytest.skip(f"optional dependency not installed: {missing}")
        raise
