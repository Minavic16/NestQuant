from pathlib import Path

from nestquant_studio.db.connection import connect, migrate
from nestquant_studio.db.repo import Repository
from nestquant_studio.services.research import ResearchService


def test_end_to_end_flow(tmp_path: Path):
    db = tmp_path / "t.db"
    conn = connect(db)
    migrate(conn)
    repo = Repository(conn)
    repo.upsert_user("op", "Op")
    svc = ResearchService(repo)

    hid = svc.create_hypothesis("T", "statement", created_by="op", meta={"seed": True})
    svc.advance_to_awaiting_approval(hid, actor="op")
    svc.approve_entry(hid, "op", note="ok")
    svc.define_search_space(
        hid,
        {
            "axes": {
                "lookback": {"type": "int_range", "min": 10, "max": 25, "step": 5},
                "threshold": {"type": "float_range", "min": 0.5, "max": 1.5, "step": 0.5},
                "cost_bps": {"type": "enum", "values": [1, 8]},
            }
        },
    )
    n = svc.generate_candidates(hid)
    assert n > 0
    reports = svc.run_ladder(hid, through_level="L3")
    assert len(reports) == 4  # L0-L3
    assert reports[0]["passed"] > 0
    out = svc.build_assessment_and_composite(hid)
    assert out["composite_id"]
    snap = repo.dashboard_snapshot()
    assert snap["counts"]["hypotheses"] == 1
    assert snap["counts"]["activity"] >= 5
    assert any(a["kind"] == "candidates.generated" for a in snap["activity"])