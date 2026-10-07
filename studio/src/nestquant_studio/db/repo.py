from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from nestquant_studio.core.hashutil import sha256_json
from nestquant_studio.core.ids import new_id
from nestquant_studio.core.state_machine import assert_transition


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _loads(s: str | None) -> Any:
    if s is None:
        return None
    return json.loads(s)


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def log_activity(
        self,
        *,
        kind: str,
        title: str,
        detail: str | None = None,
        severity: str = "info",
        entity_type: str | None = None,
        entity_id: str | None = None,
        hypothesis_id: str | None = None,
        actor: str | None = None,
        payload: dict | None = None,
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO activity_event
               (kind, severity, title, detail, entity_type, entity_id, hypothesis_id, actor, payload, at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                kind,
                severity,
                title,
                detail,
                entity_type,
                entity_id,
                hypothesis_id,
                actor,
                _j(payload) if payload is not None else None,
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_activity(self, *, limit: int = 100, hypothesis_id: str | None = None) -> list[dict]:
        if hypothesis_id:
            rows = self.conn.execute(
                "SELECT * FROM activity_event WHERE hypothesis_id = ? ORDER BY activity_id DESC LIMIT ?",
                (hypothesis_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM activity_event ORDER BY activity_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._activity_row(r) for r in rows]

    def _activity_row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["payload"] = _loads(d.get("payload"))
        return d

    def upsert_user(self, user_id: str, display_name: str, email: str | None = None, role: str = "operator") -> None:
        self.conn.execute(
            """INSERT INTO app_user (user_id, display_name, email, role)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 display_name=excluded.display_name,
                 email=excluded.email,
                 role=excluded.role""",
            (user_id, display_name, email, role),
        )
        self.conn.commit()

    def upsert_ladder(self, ladder_id: str, research_type: str, document: dict) -> None:
        self.conn.execute(
            """INSERT INTO ladder_def (ladder_id, research_type, document)
               VALUES (?, ?, ?)
               ON CONFLICT(ladder_id) DO UPDATE SET
                 document=excluded.document,
                 research_type=excluded.research_type""",
            (ladder_id, research_type, _j(document)),
        )
        self.conn.commit()

    def get_ladder(self, ladder_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM ladder_def WHERE ladder_id = ?", (ladder_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["document"] = _loads(d["document"])
        return d

    def create_search_space(self, definition: dict) -> str:
        sid = new_id()
        h = sha256_json(definition)
        self.conn.execute(
            "INSERT INTO search_space (search_space_id, definition, definition_hash) VALUES (?, ?, ?)",
            (sid, _j(definition), h),
        )
        self.conn.commit()
        return sid

    def get_search_space(self, search_space_id: str) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM search_space WHERE search_space_id = ?", (search_space_id,)
        ).fetchone()
        if not r:
            return None
        d = dict(r)
        d["definition"] = _loads(d["definition"])
        return d

    def create_hypothesis(
        self,
        *,
        title: str,
        statement: str,
        methodology: str | None = None,
        created_by: str | None = None,
        priority_score: float | None = None,
        academic_support: dict | None = None,
        meta: dict | None = None,
        ladder_id: str | None = "strategy_ladder_v1",
    ) -> str:
        hid = new_id()
        self.conn.execute(
            """INSERT INTO hypothesis
               (hypothesis_id, title, statement, methodology, status, priority_score,
                academic_support, meta, ladder_id, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'discovered', ?, ?, ?, ?, ?, ?, ?)""",
            (
                hid,
                title,
                statement,
                methodology,
                priority_score,
                _j(academic_support) if academic_support else None,
                _j(meta) if meta else None,
                ladder_id,
                created_by,
                _now(),
                _now(),
            ),
        )
        self.conn.execute(
            """INSERT INTO hypothesis_event
               (hypothesis_id, from_status, to_status, reason, actor, payload, at)
               VALUES (?, NULL, 'discovered', 'created', ?, ?, ?)""",
            (hid, created_by or "system", _j({"title": title}), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="hypothesis.created",
            title=f"Hypothesis created: {title}",
            entity_type="hypothesis",
            entity_id=hid,
            hypothesis_id=hid,
            actor=created_by or "system",
            payload={"status": "discovered"},
        )
        return hid

    def get_hypothesis(self, hypothesis_id: str) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM hypothesis WHERE hypothesis_id = ?", (hypothesis_id,)
        ).fetchone()
        if not r:
            return None
        return self._hyp_row(r)

    def list_hypotheses(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM hypothesis ORDER BY created_at DESC").fetchall()
        return [self._hyp_row(r) for r in rows]

    def _hyp_row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["academic_support"] = _loads(d.get("academic_support"))
        d["eligibility"] = _loads(d.get("eligibility"))
        d["meta"] = _loads(d.get("meta"))
        return d

    def transition_hypothesis(
        self,
        hypothesis_id: str,
        to_status: str,
        *,
        actor: str = "system",
        reason: str | None = None,
        has_approval: bool = False,
        payload: dict | None = None,
    ) -> dict:
        hyp = self.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(hypothesis_id)
        frm = hyp["status"]
        assert_transition(frm, to_status, has_approval=has_approval)
        self.conn.execute(
            "UPDATE hypothesis SET status = ?, updated_at = ? WHERE hypothesis_id = ?",
            (to_status, _now(), hypothesis_id),
        )
        self.conn.execute(
            """INSERT INTO hypothesis_event
               (hypothesis_id, from_status, to_status, reason, actor, payload, at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (hypothesis_id, frm, to_status, reason, actor, _j(payload) if payload else None, _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="hypothesis.transition",
            title=f"Hypothesis {frm} → {to_status}",
            detail=reason,
            severity="warning" if to_status == "killed" else "info",
            entity_type="hypothesis",
            entity_id=hypothesis_id,
            hypothesis_id=hypothesis_id,
            actor=actor,
            payload={"from": frm, "to": to_status},
        )
        out = self.get_hypothesis(hypothesis_id)
        assert out is not None
        return out

    def set_hypothesis_search_space(self, hypothesis_id: str, search_space_id: str) -> None:
        self.conn.execute(
            "UPDATE hypothesis SET search_space_id = ?, updated_at = ? WHERE hypothesis_id = ?",
            (search_space_id, _now(), hypothesis_id),
        )
        self.conn.commit()

    def acquire_mvp_lock(self, hypothesis_id: str) -> None:
        row = self.conn.execute(
            "SELECT hypothesis_id FROM hypothesis_lock WHERE lock_name = 'mvp_active'"
        ).fetchone()
        if row and row["hypothesis_id"] and row["hypothesis_id"] != hypothesis_id:
            raise RuntimeError(f"MVP lock held by {row['hypothesis_id']}")
        self.conn.execute(
            """INSERT INTO hypothesis_lock (lock_name, hypothesis_id, held_since)
               VALUES ('mvp_active', ?, ?)
               ON CONFLICT(lock_name) DO UPDATE SET
                 hypothesis_id=excluded.hypothesis_id,
                 held_since=excluded.held_since""",
            (hypothesis_id, _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="lock.acquired",
            title="MVP active hypothesis lock acquired",
            entity_type="hypothesis",
            entity_id=hypothesis_id,
            hypothesis_id=hypothesis_id,
            actor="system",
        )

    def release_mvp_lock(self) -> None:
        self.conn.execute(
            "UPDATE hypothesis_lock SET hypothesis_id = NULL, held_since = NULL WHERE lock_name = 'mvp_active'"
        )
        self.conn.commit()

    def get_mvp_lock(self) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM hypothesis_lock WHERE lock_name = 'mvp_active'"
        ).fetchone()
        return dict(r) if r else None

    def insert_candidates(self, hypothesis_id: str, items: list[tuple[str, dict]]) -> int:
        n = 0
        for key, params in items:
            cid = new_id()
            try:
                self.conn.execute(
                    """INSERT INTO candidate
                       (candidate_id, hypothesis_id, candidate_key, params, status, created_at)
                       VALUES (?, ?, ?, ?, 'generated', ?)""",
                    (cid, hypothesis_id, key, _j(params), _now()),
                )
                n += 1
            except sqlite3.IntegrityError:
                continue
        self.conn.commit()
        self.log_activity(
            kind="candidates.generated",
            title=f"Materialized {n} candidates",
            entity_type="hypothesis",
            entity_id=hypothesis_id,
            hypothesis_id=hypothesis_id,
            actor="system",
            payload={"count": n},
        )
        return n

    def list_candidates(self, hypothesis_id: str, status: str | None = None) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM candidate WHERE hypothesis_id = ? AND status = ? ORDER BY created_at",
                (hypothesis_id, status),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM candidate WHERE hypothesis_id = ? ORDER BY created_at",
                (hypothesis_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["params"] = _loads(d["params"])
            out.append(d)
        return out

    def candidate_counts(self, hypothesis_id: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(1) AS n FROM candidate WHERE hypothesis_id = ? GROUP BY status",
            (hypothesis_id,),
        ).fetchall()
        return {r["status"]: int(r["n"]) for r in rows}

    def update_candidate_status(
        self,
        candidate_id: str,
        to_status: str,
        *,
        from_status: str | None,
        level_id: str | None = None,
        reason: str | None = None,
        metrics: dict | None = None,
        actor: str = "system",
    ) -> None:
        self.conn.execute(
            "UPDATE candidate SET status = ?, kill_reason = ? WHERE candidate_id = ?",
            (to_status, reason if to_status == "killed" else None, candidate_id),
        )
        self.conn.execute(
            """INSERT INTO candidate_event
               (candidate_id, from_status, to_status, level_id, reason, metrics, actor, at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate_id,
                from_status,
                to_status,
                level_id,
                reason,
                _j(metrics) if metrics else None,
                actor,
                _now(),
            ),
        )

    def start_level_run(self, hypothesis_id: str, ladder_id: str, level_id: str) -> str:
        run_id = new_id()
        self.conn.execute(
            """INSERT INTO ladder_level_run
               (run_id, hypothesis_id, ladder_id, level_id, status, started_at)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (run_id, hypothesis_id, ladder_id, level_id, _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="ladder.level_started",
            title=f"Ladder level {level_id} started",
            entity_type="ladder_run",
            entity_id=run_id,
            hypothesis_id=hypothesis_id,
            actor="system",
            payload={"level_id": level_id},
        )
        return run_id

    def finish_level_run(
        self, run_id: str, report: dict, cost: dict | None = None, status: str = "done"
    ) -> None:
        self.conn.execute(
            """UPDATE ladder_level_run
               SET status = ?, report = ?, cost = ?, finished_at = ?
               WHERE run_id = ?""",
            (status, _j(report), _j(cost) if cost else None, _now(), run_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM ladder_level_run WHERE run_id = ?", (run_id,)
        ).fetchone()
        self.log_activity(
            kind="ladder.level_finished",
            title=f"Ladder level {row['level_id']} {status}",
            entity_type="ladder_run",
            entity_id=run_id,
            hypothesis_id=row["hypothesis_id"],
            actor="system",
            payload=report,
            severity="info" if status == "done" else "error",
        )

    def add_level_result(
        self,
        run_id: str,
        candidate_id: str,
        level_id: str,
        passed: bool,
        metrics: dict | None = None,
        kill_reason: str | None = None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO level_candidate_result
               (run_id, candidate_id, level_id, passed, metrics, kill_reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                candidate_id,
                level_id,
                1 if passed else 0,
                _j(metrics) if metrics else None,
                kill_reason,
            ),
        )

    def list_level_runs(self, hypothesis_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM ladder_level_run WHERE hypothesis_id = ? ORDER BY started_at",
            (hypothesis_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["report"] = _loads(d.get("report"))
            d["cost"] = _loads(d.get("cost"))
            out.append(d)
        return out

    def create_approval(
        self,
        *,
        subject_type: str,
        subject_id: str,
        subject_hash: str,
        approver_id: str,
        subject_version: int | None = None,
        note: str | None = None,
    ) -> str:
        aid = new_id()
        self.conn.execute(
            """INSERT INTO approval
               (approval_id, subject_type, subject_id, subject_version, subject_hash, approver_id, note, at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (aid, subject_type, subject_id, subject_version, subject_hash, approver_id, note, _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="approval.recorded",
            title=f"Approval: {subject_type}",
            detail=note,
            severity="success",
            entity_type=subject_type,
            entity_id=subject_id,
            actor=approver_id,
            payload={"subject_hash": subject_hash, "version": subject_version},
        )
        return aid

    def save_strategy_composite(
        self,
        composite_id: str,
        version: int,
        title: str,
        body: dict,
        status: str,
        hypothesis_id: str | None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO strategy_composite
               (composite_id, version, hypothesis_id, title, status, body, body_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (composite_id, version, hypothesis_id, title, status, _j(body), sha256_json(body), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="composite.saved",
            title=f"Strategy Composite v{version}: {title}",
            entity_type="strategy_composite",
            entity_id=composite_id,
            hypothesis_id=hypothesis_id,
            payload={"status": status, "version": version},
        )

    def list_composites(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM strategy_composite ORDER BY created_at DESC"
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["body"] = _loads(d["body"])
            out.append(d)
        return out

    def save_risk_constraint_set(
        self, rcs_id: str, version: int, title: str, body: dict, status: str
    ) -> None:
        self.conn.execute(
            """INSERT INTO risk_constraint_set
               (rcs_id, version, title, status, body, body_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rcs_id, version, title, status, _j(body), sha256_json(body), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="risk.rcs_saved",
            title=f"RiskConstraintSet v{version}: {title}",
            entity_type="risk_constraint_set",
            entity_id=rcs_id,
            payload={"status": status},
        )

    def save_portfolio(
        self, portfolio_id: str, version: int, title: str, body: dict, status: str
    ) -> None:
        self.conn.execute(
            """INSERT INTO portfolio_declaration
               (portfolio_id, version, title, status, body, body_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (portfolio_id, version, title, status, _j(body), sha256_json(body), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="portfolio.saved",
            title=f"Portfolio v{version}: {title}",
            entity_type="portfolio_declaration",
            entity_id=portfolio_id,
            payload={"status": status},
        )

    def save_regime_model(
        self, regime_model_id: str, version: int, title: str, body: dict, status: str
    ) -> None:
        self.conn.execute(
            """INSERT INTO regime_model
               (regime_model_id, version, title, status, body, body_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (regime_model_id, version, title, status, _j(body), sha256_json(body), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="regime.saved",
            title=f"RegimeModel v{version}: {title}",
            entity_type="regime_model",
            entity_id=regime_model_id,
            payload={"status": status},
        )

    def create_engineering_task(self, title: str, contract: dict) -> str:
        tid = new_id()
        self.conn.execute(
            """INSERT INTO engineering_task
               (task_id, title, status, contract, created_at, updated_at)
               VALUES (?, ?, 'queued', ?, ?, ?)""",
            (tid, title, _j(contract), _now(), _now()),
        )
        self.conn.commit()
        self.log_activity(
            kind="engineering.task_created",
            title=f"Engineering task: {title}",
            entity_type="engineering_task",
            entity_id=tid,
            actor="system",
        )
        return tid

    def set_audit_verdict(
        self, task_id: str, verdict: str, auditor: str, findings: dict | None = None
    ) -> str:
        vid = new_id()
        self.conn.execute(
            """INSERT INTO audit_verdict
               (verdict_id, task_id, verdict, findings, auditor, at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (vid, task_id, verdict, _j(findings) if findings else None, auditor, _now()),
        )
        status = "ok" if verdict == "OK" else "failed"
        self.conn.execute(
            "UPDATE engineering_task SET status = ?, updated_at = ? WHERE task_id = ?",
            (status, _now(), task_id),
        )
        self.conn.commit()
        self.log_activity(
            kind="engineering.audit",
            title=f"Audit {verdict}",
            severity="success" if verdict == "OK" else "error",
            entity_type="engineering_task",
            entity_id=task_id,
            actor=auditor,
            payload=findings,
        )
        return vid

    def list_engineering(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            """SELECT task_id, title, status, git_commit, created_at, updated_at
               FROM engineering_task ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def dashboard_snapshot(self) -> dict:
        hyps = self.list_hypotheses()
        lock = self.get_mvp_lock()
        activity = self.list_activity(limit=80)
        jobs = [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM job ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        ]
        for j in jobs:
            j["payload"] = _loads(j.get("payload"))
        eng = self.list_engineering()
        composites = self.list_composites()
        counts = {
            "hypotheses": len(hyps),
            "active_like": sum(
                1
                for h in hyps
                if h["status"]
                not in ("killed", "archived", "discovered", "filtered", "ranked")
            ),
            "composites": len(composites),
            "activity": len(activity),
            "engineering_open": sum(
                1 for e in eng if e["status"] not in ("ok", "failed", "cancelled")
            ),
        }
        per_hyp = []
        for h in hyps:
            cc = self.candidate_counts(h["hypothesis_id"])
            runs = self.list_level_runs(h["hypothesis_id"])
            per_hyp.append(
                {
                    "hypothesis": h,
                    "candidate_counts": cc,
                    "level_runs": runs,
                    "candidates_total": sum(cc.values()),
                }
            )
        return {
            "generated_at": _now(),
            "counts": counts,
            "lock": lock,
            "hypotheses": per_hyp,
            "activity": activity,
            "jobs": jobs,
            "engineering": eng,
            "composites": composites,
        }
