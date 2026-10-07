"""Generate the shared circuit-breaker fixtures from the Python reference.

Run:  python contracts/fixtures/generate_breakers.py
The Rust crate (nqts/rust/risk-engine) replays this file; a Python test fails
if the committed file drifts from what the Python implementation produces.
"""
import json
import logging
import os
from pathlib import Path

os.environ.setdefault("NESTQUANT_SKIP_LIVE_CHECK", "1")
from nestquant.production.risk.circuit_breakers import (  # noqa: E402
    WinRateBreaker, SlippageBreaker, DrawdownPaceBreaker, ProfitFactorBreaker)

FIXTURE_PATH = Path(__file__).with_name("breakers.json")


def build() -> dict:
    logging.disable(logging.CRITICAL)
    out = {"winrate": [], "slippage": [], "drawdown_pace": [], "profit_factor": []}

    # WinRate: (pnl sequence) -> final state after check at the end
    for name, seq in {
        "all_losses_25": [-1.0] * 25,
        "healthy_30": ([1.0, -1.0] * 15),
        "bad_20_good_history": [1.0] * 10 + [-1.0] * 15,
        "too_few_trades": [-1.0] * 19,
        "losing_30": [-1.0] * 30,
    }.items():
        b = WinRateBreaker(0.40, 0.45)
        for p in seq: b.record_trade(p)
        trig = b.check()
        out["winrate"].append({"name": name, "pnls": seq, "triggered": trig,
                               "paused": b.paused, "hard_stopped": b.hard_stopped,
                               "events": len(b.events)})

    for name, seq in {
        "three_consecutive_high": [5.0, 5.0, 5.0],
        "streak_reset": [5.0, 5.0, 1.0, 5.0],
        "avg_creep": [6.5] * 10,
        "quiet": [0.5] * 12,
    }.items():
        b = SlippageBreaker(4.8, 3, 6.0)
        for s in seq: b.record_slippage(s)
        trig = b.check()
        out["slippage"].append({"name": name, "slippages": seq, "triggered": trig,
                                "paused": b.paused, "hard_stopped": b.hard_stopped,
                                "events": len(b.events)})

    for name, steps in {
        "fast_hard": [[100.0, 100.0], [90.0, 100.0]],
        "soft_only": [[100.0, 100.0], [93.5, 100.0]],
        "slow_dd_ignored": [[100.0, 100.0]] * 30 + [[90.0, 100.0]],
        "no_dd": [[100.0, 100.0]] * 5,
    }.items():
        b = DrawdownPaceBreaker(6.0, 15, 9.0, 25)
        for eq, pk in steps: b.record_trade(0.0, eq, pk)
        trig = b.check()
        out["drawdown_pace"].append({"name": name, "steps": steps, "triggered": trig,
                                     "paused": b.paused, "hard_stopped": b.hard_stopped,
                                     "events": len(b.events)})

    for name, seq in {
        "losing_window": [1.0] * 5 + [-1.0] * 15,
        "winning_window": [2.0] * 10 + [-1.0] * 10,
        "no_losses": [1.0] * 20,
        "short_window": [-1.0] * 10,
    }.items():
        b = ProfitFactorBreaker(1.0, 20)
        for p in seq: b.record_trade(p)
        trig = b.check()
        out["profit_factor"].append({"name": name, "pnls": seq, "triggered": trig,
                                     "paused": b.paused, "hard_stopped": b.hard_stopped,
                                     "events": len(b.events)})

    return out


if __name__ == "__main__":
    FIXTURE_PATH.write_text(json.dumps(build(), indent=1))
    print("wrote", FIXTURE_PATH)
