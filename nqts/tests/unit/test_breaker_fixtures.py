"""Guard: shared breaker fixtures must match the Python reference implementation.

The Rust risk engine replays contracts/fixtures/breakers.json. If the Python
breakers change, regenerate with `python contracts/fixtures/generate_breakers.py`
and make the Rust crate agree — otherwise CI fails on one side or the other.
"""
import importlib.util
import json
from pathlib import Path

GEN = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "generate_breakers.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_breakers", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixtures_match_python_reference():
    mod = _load()
    committed = json.loads(mod.FIXTURE_PATH.read_text())
    assert committed == mod.build(), "breakers.json is stale: rerun generate_breakers.py"


def test_fixtures_cover_every_breaker_and_both_outcomes():
    data = json.loads(_load().FIXTURE_PATH.read_text())
    assert set(data) == {"winrate", "slippage", "drawdown_pace", "profit_factor"}
    for name, cases in data.items():
        assert any(c["triggered"] for c in cases), f"{name}: no triggering case"
        assert any(not c["triggered"] for c in cases), f"{name}: no quiet case"
