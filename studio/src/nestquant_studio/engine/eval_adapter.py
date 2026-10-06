"""Evaluation adapter interface — real backtesters plug in here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class EvalRequest:
    candidate_id: str
    candidate_key: str
    params: dict[str, Any]
    level_id: str
    eval_config_id: str | None = None
    dataset_ref: str | None = None


@dataclass
class EvalResult:
    ok: bool
    passed: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    kill_reason: str | None = None
    error: str | None = None
    cost: dict[str, Any] = field(default_factory=dict)


class EvalAdapter(Protocol):
    def evaluate(self, req: EvalRequest) -> EvalResult: ...


class ToyParamEvalAdapter:
    """
    Deterministic placeholder evaluator for pipeline testing.
    Does NOT encode domain entities — thresholds come from eval_config document.
    Pass rules use only generic param keys present in the candidate.
    """

    def __init__(self, configs: dict[str, dict] | None = None):
        self.configs = configs or {}

    def evaluate(self, req: EvalRequest) -> EvalResult:
        cfg = self.configs.get(req.eval_config_id or "", {})
        thresholds = cfg.get("thresholds") or {}
        params = req.params or {}

        if req.level_id == "L0":
            # Sanity: must have at least one param
            if not params:
                return EvalResult(ok=True, passed=False, kill_reason="error", metrics={"ran": 0})
            return EvalResult(ok=True, passed=True, metrics={"ran": 1, "n_params": len(params)})

        # Generic numeric gate: if config names a param threshold, apply it
        # Example thresholds: {"lookback_min": 15, "score_min": 0.5}
        metrics: dict[str, Any] = dict(params)
        score = 0.0
        numeric_vals = [float(v) for v in params.values() if isinstance(v, (int, float))]
        if numeric_vals:
            score = sum(numeric_vals) / len(numeric_vals)
        metrics["score_like"] = round(score, 6)

        for key, vmin in thresholds.items():
            if key.endswith("_min"):
                p = key[: -len("_min")]
                if p in params and isinstance(params[p], (int, float)):
                    if float(params[p]) < float(vmin):
                        return EvalResult(
                            ok=True,
                            passed=False,
                            metrics=metrics,
                            kill_reason="below_metric",
                        )
            if key.endswith("_max"):
                p = key[: -len("_max")]
                if p in params and isinstance(params[p], (int, float)):
                    if float(params[p]) > float(vmax := vmin):
                        return EvalResult(
                            ok=True,
                            passed=False,
                            metrics=metrics,
                            kill_reason="below_metric",
                        )

        # Default L1+: require score_like >= threshold if provided
        smin = thresholds.get("score_like_min")
        if smin is not None and score < float(smin):
            return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="below_metric")

        # L3 uneconomic toy: if cost_bps present and high
        if req.level_id == "L3":
            cost = float(params.get("cost_bps", 0) or 0)
            metrics["cost_bps"] = cost
            max_cost = float(thresholds.get("cost_bps_max", 1e9))
            if cost > max_cost:
                return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="uneconomic")

        return EvalResult(ok=True, passed=True, metrics=metrics)

class DeterministicBacktestAdapter:
    """Deterministic, cost-aware stand-in for a real backtester.

    v0.1 does not run a live market simulation; instead it deterministically
    derives reproducible metrics from the candidate key + params (stable
    hashing) while honoring the eval_config thresholds. The output contract
    (metrics / kill_reason / cost) matches the real EvalAdapter so the ladder,
    repo, and audit layers do not change when a real backtester is plugged in.
    """

    def __init__(self, configs: dict[str, dict] | None = None):
        self.configs = configs or {}

    def evaluate(self, req: EvalRequest) -> EvalResult:
        import hashlib

        cfg = self.configs.get(req.eval_config_id or "", {})
        thresholds = cfg.get("thresholds") or {}
        params = req.params or {}

        seed = int(
            hashlib.sha256(
                f"{req.candidate_key}|{sorted(params.items())}|{req.level_id}".encode()
            ).hexdigest()[:8],
            16,
        )
        # reproducible pseudo-metrics in [0,1)
        ev = (seed % 1000) / 1000.0
        sharpe_like = round((ev * 4.0) - 1.0, 3)
        win_rate = round(0.35 + ev * 0.3, 3)
        drawdown = round(0.05 + ev * 0.5, 3)
        metrics: dict[str, Any] = {
            "ev_score": round(ev, 4),
            "sharpe_like": sharpe_like,
            "win_rate": win_rate,
            "max_drawdown": drawdown,
            "ran": 1,
        }

        if req.level_id == "L0":
            if not params:
                return EvalResult(ok=True, passed=False, kill_reason="error", metrics={"ran": 0})
            return EvalResult(ok=True, passed=True, metrics=metrics)

        # Generic thresholds: score_min, sharpe_like_min, drawdown_max, etc.
        for key, vmin in thresholds.items():
            if key.endswith("_min"):
                p = key[: -len("_min")]
                if metrics.get(p, None) is not None and float(metrics[p]) < float(vmin):
                    return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="below_metric")
            if key.endswith("_max"):
                p = key[: -len("_max")]
                if metrics.get(p, None) is not None and float(metrics[p]) > float(vmin):
                    return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="above_max")

        smin = thresholds.get("score_like_min")
        if smin is not None and ev < (float(smin) / 50.0):
            return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="below_metric")

        if req.level_id == "L3":
            cost = float(params.get("cost_bps", 0) or 0)
            max_cost = float(thresholds.get("cost_bps_max", 1e9))
            if cost > max_cost:
                return EvalResult(ok=True, passed=False, metrics=metrics, kill_reason="uneconomic")

        return EvalResult(ok=True, passed=True, metrics=metrics)
