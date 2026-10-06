"""Seed generic demo data — no production domain entities hardcoded as constants."""
from __future__ import annotations

import os
from pathlib import Path

from nestquant_studio.db.connection import connect, db_path, migrate
from nestquant_studio.db.repo import Repository
from nestquant_studio.services.research import ResearchService


def seed(path: Path | None = None) -> dict:
    if path is None:
        path = db_path()
    if path.exists():
        path.unlink()
    conn = connect(path)
    migrate(conn)
    repo = Repository(conn)
    svc = ResearchService(repo)

    # Operator identity from env when available — generic fallback id
    operator_id = os.environ.get("STUDIO_OPERATOR_ID", "user-operator")
    operator_name = os.environ.get("STUDIO_OPERATOR_NAME", "Operator")
    operator_email = os.environ.get("STUDIO_OPERATOR_EMAIL")
    repo.upsert_user(operator_id, operator_name, operator_email, role="operator")

    svc.ensure_ladder()

    # Generic demo hypothesis — parameters are abstract axes, not market symbols baked into code paths
    hid = svc.create_hypothesis(
        title="Demo: mean-reversion intensity vs lookback",
        statement=(
            "A generic mean-reversion intensity signal may exhibit short-horizon "
            "predictive structure when lookback and threshold vary within a bounded search space."
        ),
        methodology="Toy eval adapter; replace with real backtester eval configs in production.",
        created_by=operator_id,
        priority_score=0.7,
        academic_support={"score": 0.4, "notes": "demo only", "refs": []},
        meta={"seed": True, "demo": True},
    )
    svc.advance_to_awaiting_approval(hid, actor=operator_id)
    svc.approve_entry(hid, operator_id, note="Seed demo entry approval")

    # Search space uses abstract axis names — values are data, not code-level domain enums
    definition = {
        "axes": {
            "lookback": {"type": "int_range", "min": 5, "max": 30, "step": 5},
            "threshold": {"type": "float_range", "min": 0.5, "max": 2.0, "step": 0.5},
            "cost_bps": {"type": "enum", "values": [1, 3, 7]},
        },
        "exclude": [],
        "include": [],
    }
    svc.define_search_space(hid, definition, actor=operator_id)
    n = svc.generate_candidates(hid, actor=operator_id)
    reports = svc.run_ladder(hid, through_level="L3", actor="system")
    composite = svc.build_assessment_and_composite(hid, actor="system")

    # Sample risk constraint set (generic limits)
    rcs_id = "rcs-demo"
    repo.save_risk_constraint_set(
        rcs_id,
        1,
        "Demo portfolio hard limits",
        {
            "risk_constraint_set_id": rcs_id,
            "version": 1,
            "status": "approved",
            "scope": "portfolio",
            "constraints": [
                {"type": "max_gross_exposure", "value": 1.5},
                {"type": "max_drawdown_halt", "value": 0.15},
                {"type": "max_symbol_weight", "value": 0.25},
            ],
            "violation_policy": {"on_breach": "scale_down", "severity": "hard"},
            "evidence_hashes": [],
        },
        "approved",
    )

    # Engineering task demo
    tid = repo.create_engineering_task(
        "Wire real EvalAdapter to backtester",
        {"acceptance": ["implements EvalAdapter", "deterministic metrics keys"]},
    )
    repo.set_audit_verdict(tid, "OK", auditor="auditor-slot", findings={"notes": "seed placeholder"})

    snap = repo.dashboard_snapshot()
    return {
        "db_path": str(path),
        "hypothesis_id": hid,
        "candidates": n,
        "ladder_reports": reports,
        "composite_id": composite["composite_id"],
        "activity": snap["counts"]["activity"],
    }


def main() -> None:
    result = seed()
    print(result)


if __name__ == "__main__":
    main()