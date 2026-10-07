"""Research lifecycle service — deterministic orchestration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nestquant_studio.core.hashutil import sha256_json
from nestquant_studio.core.ids import new_id
from nestquant_studio.core.search_space import SearchSpace
from nestquant_studio.db.repo import Repository
from nestquant_studio.engine.eval_adapter import DeterministicBacktestAdapter
from nestquant_studio.engine.ladder_runner import LadderRunner

LADDER_PATH = Path(__file__).resolve().parents[3] / "schemas" / "strategy_ladder_v1.json"

# Generic eval configs — no domain symbols hardcoded
DEFAULT_EVAL_CONFIGS = {
    "strategy_l0_v1": {"thresholds": {}},
    "strategy_l1_v1": {"thresholds": {"lookback_min": 15, "score_like_min": 5}},
    "strategy_l2_v1": {"thresholds": {"lookback_min": 15, "score_like_min": 8}},
    "strategy_l3_v1": {"thresholds": {"lookback_min": 15, "cost_bps_max": 5}},
    "strategy_l4_v1": {"thresholds": {"lookback_min": 20}},
    "strategy_l5_v1": {"thresholds": {}},
}


class ResearchService:
    def __init__(self, repo: Repository):
        self.repo = repo
        self._ladder_doc: dict | None = None

    def ensure_ladder(self) -> dict:
        if self._ladder_doc is None:
            self._ladder_doc = json.loads(LADDER_PATH.read_text(encoding="utf-8"))
        self.repo.upsert_ladder(
            self._ladder_doc["ladder_id"],
            self._ladder_doc["research_type"],
            self._ladder_doc,
        )
        return self._ladder_doc

    def create_hypothesis(
        self,
        title: str,
        statement: str,
        *,
        methodology: str | None = None,
        created_by: str | None = None,
        meta: dict | None = None,
        priority_score: float | None = None,
        academic_support: dict | None = None,
    ) -> str:
        self.ensure_ladder()
        return self.repo.create_hypothesis(
            title=title,
            statement=statement,
            methodology=methodology,
            created_by=created_by,
            meta=meta,
            priority_score=priority_score,
            academic_support=academic_support,
        )

    def advance_to_awaiting_approval(self, hypothesis_id: str, actor: str = "system") -> dict:
        # discovered -> filtered -> ranked -> awaiting_entry_approval
        for to in ("filtered", "ranked", "awaiting_entry_approval"):
            hyp = self.repo.get_hypothesis(hypothesis_id)
            assert hyp
            if hyp["status"] == to:
                continue
            if hyp["status"] == "awaiting_entry_approval":
                break
            self.repo.transition_hypothesis(hypothesis_id, to, actor=actor, reason="pipeline")
        return self.repo.get_hypothesis(hypothesis_id)  # type: ignore

    def approve_entry(self, hypothesis_id: str, approver_id: str, note: str | None = None) -> dict:
        hyp = self.repo.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        if hyp["status"] != "awaiting_entry_approval":
            raise RuntimeError(f"expected awaiting_entry_approval, got {hyp['status']}")
        h = sha256_json({"hypothesis_id": hypothesis_id, "statement": hyp["statement"]})
        self.repo.create_approval(
            subject_type="hypothesis_entry",
            subject_id=hypothesis_id,
            subject_hash=h,
            approver_id=approver_id,
            note=note,
        )
        self.repo.acquire_mvp_lock(hypothesis_id)
        return self.repo.transition_hypothesis(
            hypothesis_id,
            "active",
            actor=approver_id,
            reason=note or "entry approved",
            has_approval=True,
        )

    def define_search_space(self, hypothesis_id: str, definition: dict, actor: str = "system") -> str:
        hyp = self.repo.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        if hyp["status"] not in ("active", "search_defined"):
            # allow from active only primarily
            if hyp["status"] == "active":
                pass
            else:
                raise RuntimeError(f"cannot define search space in status {hyp['status']}")
        sid = self.repo.create_search_space(definition)
        self.repo.set_hypothesis_search_space(hypothesis_id, sid)
        if hyp["status"] == "active":
            self.repo.transition_hypothesis(
                hypothesis_id, "search_defined", actor=actor, reason="search space attached"
            )
        self.repo.log_activity(
            kind="search_space.defined",
            title="Search space defined",
            entity_type="search_space",
            entity_id=sid,
            hypothesis_id=hypothesis_id,
            actor=actor,
            payload={"definition_hash": sha256_json(definition)},
        )
        return sid

    def generate_candidates(self, hypothesis_id: str, *, limit: int | None = None, actor: str = "system") -> int:
        hyp = self.repo.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        if not hyp.get("search_space_id"):
            raise RuntimeError("search space required")
        if hyp["status"] == "search_defined":
            self.repo.transition_hypothesis(hypothesis_id, "generating", actor=actor)
        ss = self.repo.get_search_space(hyp["search_space_id"])
        assert ss
        items = SearchSpace(ss["definition"]).materialize(limit=limit)
        n = self.repo.insert_candidates(hypothesis_id, items)
        # move to low_cost_filter after generation
        hyp2 = self.repo.get_hypothesis(hypothesis_id)
        if hyp2 and hyp2["status"] == "generating":
            self.repo.transition_hypothesis(
                hypothesis_id, "low_cost_filter", actor=actor, reason=f"generated {n}"
            )
        return n

    def run_ladder(
        self,
        hypothesis_id: str,
        *,
        through_level: str = "L2",
        actor: str = "system",
        eval_configs: dict | None = None,
    ) -> list[dict]:
        ladder = self.ensure_ladder()
        hyp = self.repo.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        if hyp["status"] == "low_cost_filter":
            self.repo.transition_hypothesis(hypothesis_id, "in_ladder", actor=actor)
        adapter = DeterministicBacktestAdapter(eval_configs or DEFAULT_EVAL_CONFIGS)
        runner = LadderRunner(self.repo, adapter)
        ordered = [lv["level_id"] for lv in ladder["levels"]]
        if through_level not in ordered:
            raise KeyError(through_level)
        stop_idx = ordered.index(through_level)
        reports = []
        for level_id in ordered[: stop_idx + 1]:
            reports.append(
                runner.run_level(
                    hypothesis_id=hypothesis_id,
                    ladder=ladder,
                    level_id=level_id,
                )
            )
        return reports

    def build_assessment_and_composite(
        self,
        hypothesis_id: str,
        *,
        title: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        hyp = self.repo.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        # survivors = highest level reached among non-killed
        cands = self.repo.list_candidates(hypothesis_id)
        alive = [c for c in cands if c["status"] != "killed"]
        # prefer L5..L0
        rank = {f"L{i}": i for i in range(6)}
        rank["survived"] = 6
        rank["generated"] = -1
        survivors = sorted(alive, key=lambda c: rank.get(c["status"], 0), reverse=True)
        top = survivors[:20]

        profile_body = {
            "hypothesis_id": hypothesis_id,
            "survivor_count": len(alive),
            "killed_count": sum(1 for c in cands if c["status"] == "killed"),
            "top_survivors": [
                {
                    "candidate_id": c["candidate_id"],
                    "candidate_key": c["candidate_key"],
                    "status": c["status"],
                    "params": c["params"],
                }
                for c in top
            ],
            "notes": "Auto-generated assessment profile from ladder survivors.",
        }
        from nestquant_studio.core.ids import new_id as _new

        profile_id = _new()
        self.repo.conn.execute(
            """INSERT INTO assessment_profile (profile_id, hypothesis_id, body, body_hash, created_at)
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (profile_id, hypothesis_id, json.dumps(profile_body), sha256_json(profile_body)),
        )
        self.repo.conn.commit()

        if hyp["status"] == "in_ladder":
            self.repo.transition_hypothesis(hypothesis_id, "assessed", actor=actor)

        capabilities = []
        if top:
            capabilities.append(
                {
                    "capability_id": new_id("cap_"),
                    "role": "core",
                    "survivor_candidate_ids": [c["candidate_id"] for c in top[:5]],
                    "summary": "Top ladder survivors grouped as core capability (generic).",
                    "evidence_hashes": [],
                }
            )

        composite_id = new_id("sc_")
        body = {
            "composite_id": composite_id,
            "version": 1,
            "status": "proposed",
            "title": title or f"Composite for {hyp['title']}",
            "hypothesis_id": hypothesis_id,
            "assessment_profile_ref": {"id": profile_id, "hash": sha256_json(profile_body)},
            "capabilities": capabilities,
            "assembly": {
                "kind": "single" if len(capabilities) <= 1 else "ensemble",
                "graph": {"nodes": [], "edges": []},
                "params_frozen": True,
            },
            "runtime_contract": {
                "inputs": ["bars"],
                "outputs": ["target_position"],
                "statefulness": "bar_state",
                "max_leverage": 1.0,
            },
            "risk_hooks": {"must_respect_constraint_set_ids": [], "local_limits": {}},
            "lineage": {
                "ladder_version": "strategy_ladder_v1",
                "created_from_survivors_count": len(top),
                "evidence_root": sha256_json(profile_body),
            },
            "approval": None,
        }
        self.repo.save_strategy_composite(
            composite_id, 1, body["title"], body, "proposed", hypothesis_id
        )
        if self.repo.get_hypothesis(hypothesis_id)["status"] == "assessed":
            self.repo.transition_hypothesis(
                hypothesis_id, "composite_proposed", actor=actor, reason="composite drafted"
            )
        return {"profile_id": profile_id, "composite_id": composite_id, "body": body}

    def approve_composite(
        self, composite_id: str, version: int, approver_id: str, note: str | None = None
    ) -> None:
        rows = self.repo.conn.execute(
            "SELECT * FROM strategy_composite WHERE composite_id = ? AND version = ?",
            (composite_id, version),
        ).fetchone()
        if not rows:
            raise KeyError(composite_id)
        json.loads(rows["body"])  # stored body must be well-formed JSON before approval
        self.repo.create_approval(
            subject_type="strategy_composite",
            subject_id=composite_id,
            subject_version=version,
            subject_hash=rows["body_hash"],
            approver_id=approver_id,
            note=note,
        )
        self.repo.conn.execute(
            "UPDATE strategy_composite SET status = 'approved' WHERE composite_id = ? AND version = ?",
            (composite_id, version),
        )
        self.repo.conn.commit()
        hid = rows["hypothesis_id"]
        if hid:
            hyp = self.repo.get_hypothesis(hid)
            if hyp and hyp["status"] == "composite_proposed":
                self.repo.transition_hypothesis(
                    hid, "composite_approved", actor=approver_id, has_approval=True, reason=note
                )
        self.repo.log_activity(
            kind="composite.approved",
            title=f"Composite approved: {rows['title']}",
            severity="success",
            entity_type="strategy_composite",
            entity_id=composite_id,
            hypothesis_id=hid,
            actor=approver_id,
        )