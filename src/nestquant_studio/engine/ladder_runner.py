"""Deterministic ladder runner — promotion/kill bookkeeping."""
from __future__ import annotations

from typing import Any

from nestquant_studio.db.repo import Repository
from nestquant_studio.engine.eval_adapter import EvalAdapter, EvalRequest


class LadderRunner:
    def __init__(self, repo: Repository, adapter: EvalAdapter):
        self.repo = repo
        self.adapter = adapter

    def run_level(
        self,
        *,
        hypothesis_id: str,
        ladder: dict,
        level_id: str,
        candidate_statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        levels = {lv["level_id"]: lv for lv in ladder.get("levels", [])}
        if level_id not in levels:
            raise KeyError(level_id)
        level = levels[level_id]
        ladder_id = ladder["ladder_id"]
        budget = level.get("budgets") or {}
        max_c = budget.get("max_candidates")

        # Which candidates enter this level
        if candidate_statuses is None:
            if level_id == "L0":
                candidate_statuses = ["generated"]
            else:
                # previous level id as status
                prev = None
                ordered = [lv["level_id"] for lv in ladder["levels"]]
                idx = ordered.index(level_id)
                prev = ordered[idx - 1] if idx > 0 else "generated"
                candidate_statuses = [prev, "survived"]

        candidates: list[dict] = []
        for st in candidate_statuses:
            candidates.extend(self.repo.list_candidates(hypothesis_id, status=st))
        # de-dupe by id preserving order
        seen = set()
        uniq = []
        for c in candidates:
            if c["candidate_id"] in seen:
                continue
            seen.add(c["candidate_id"])
            uniq.append(c)
        candidates = uniq
        if max_c is not None:
            candidates = candidates[: int(max_c)]

        run_id = self.repo.start_level_run(hypothesis_id, ladder_id, level_id)
        passed_n = 0
        killed_n = 0
        results_summary = []

        try:
            for c in candidates:
                req = EvalRequest(
                    candidate_id=c["candidate_id"],
                    candidate_key=c["candidate_key"],
                    params=c["params"],
                    level_id=level_id,
                    eval_config_id=level.get("eval_config_id"),
                )
                result = self.adapter.evaluate(req)
                self.repo.add_level_result(
                    run_id,
                    c["candidate_id"],
                    level_id,
                    passed=result.passed,
                    metrics=result.metrics,
                    kill_reason=result.kill_reason,
                )
                from_status = c["status"]
                if result.passed:
                    to_status = level_id
                    self.repo.update_candidate_status(
                        c["candidate_id"],
                        to_status,
                        from_status=from_status,
                        level_id=level_id,
                        metrics=result.metrics,
                    )
                    passed_n += 1
                else:
                    self.repo.update_candidate_status(
                        c["candidate_id"],
                        "killed",
                        from_status=from_status,
                        level_id=level_id,
                        reason=result.kill_reason or "below_metric",
                        metrics=result.metrics,
                    )
                    killed_n += 1
                results_summary.append(
                    {
                        "candidate_id": c["candidate_id"],
                        "passed": result.passed,
                        "kill_reason": result.kill_reason,
                    }
                )
            self.repo.conn.commit()
            report = {
                "level_id": level_id,
                "input": len(candidates),
                "passed": passed_n,
                "killed": killed_n,
            }
            self.repo.finish_level_run(run_id, report=report, status="done")
            return {"run_id": run_id, **report, "results": results_summary}
        except Exception as e:
            self.repo.finish_level_run(
                run_id, report={"error": str(e)}, status="failed"
            )
            raise