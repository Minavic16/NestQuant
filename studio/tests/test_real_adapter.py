"""SimulatedExecutionAdapter runs the real simulator+evaluator deterministically."""

from nestquant_studio.engine.eval_adapter import EvalRequest, SimulatedExecutionAdapter

CFG = {"s1": {"thresholds": {"profit_factor_min": 0.0}}}


def _run():
    a = SimulatedExecutionAdapter(CFG)
    return a.evaluate(EvalRequest("c1", "c1-key", {"sl_pct": 0.01, "tp_pct": 0.02}, "L1", eval_config_id="s1"))


def test_deterministic_and_real_metrics():
    r1, r2 = _run(), _run()
    assert r1.metrics == r2.metrics, "adapter is not deterministic"
    for k in ("total_trades", "win_rate", "profit_factor", "max_drawdown", "sharpe_ratio"):
        assert k in r1.metrics
    assert r1.metrics["total_trades"] > 0


def test_threshold_kill():
    a = SimulatedExecutionAdapter({"s1": {"thresholds": {"win_rate_min": 1.5}}})
    r = a.evaluate(EvalRequest("c2", "k2", {}, "L1", eval_config_id="s1"))
    assert r.passed is False and r.kill_reason in ("below_metric", "error", "no_trades")
