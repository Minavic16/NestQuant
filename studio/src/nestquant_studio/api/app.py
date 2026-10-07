"""FastAPI application — Studio API + operator dashboard."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from nestquant_studio.db.connection import connect, db_path, migrate
from nestquant_studio.db.repo import Repository
from nestquant_studio.services.research import ResearchService

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"

app = FastAPI(title="NestQuant Studio", version="0.1.0")


def get_repo() -> Repository:
    conn = connect()
    # idempotent migrate
    migrate(conn)
    return Repository(conn)


class HypothesisCreate(BaseModel):
    title: str
    statement: str
    methodology: str | None = None
    priority_score: float | None = None
    meta: dict[str, Any] | None = None


class SearchSpaceBody(BaseModel):
    definition: dict[str, Any]


class ApproveBody(BaseModel):
    note: str | None = None
    approver_id: str | None = None


class LadderBody(BaseModel):
    through_level: str = "L2"


@app.get("/readyz")
def readyz():
    return {"status": "ok"}


@app.get("/api/health")
def health():
    p = db_path()
    return {"status": "ok", "db_path": str(p), "db_exists": p.exists()}


@app.get("/api/dashboard")
def dashboard():
    repo = get_repo()
    return repo.dashboard_snapshot()


@app.get("/api/activity")
def activity(limit: int = 100, hypothesis_id: str | None = None):
    repo = get_repo()
    return repo.list_activity(limit=limit, hypothesis_id=hypothesis_id)


@app.get("/api/hypotheses")
def hypotheses():
    repo = get_repo()
    return repo.list_hypotheses()


@app.get("/api/hypotheses/{hypothesis_id}")
def hypothesis_detail(hypothesis_id: str):
    repo = get_repo()
    hyp = repo.get_hypothesis(hypothesis_id)
    if not hyp:
        raise HTTPException(404, "hypothesis not found")
    return {
        "hypothesis": hyp,
        "candidates": repo.candidate_counts(hypothesis_id),
        "level_runs": repo.list_level_runs(hypothesis_id),
        "activity": repo.list_activity(limit=50, hypothesis_id=hypothesis_id),
    }


@app.post("/api/hypotheses")
def create_hypothesis(body: HypothesisCreate):
    repo = get_repo()
    svc = ResearchService(repo)
    operator = os.environ.get("STUDIO_OPERATOR_ID", "user-operator")
    hid = svc.create_hypothesis(
        body.title,
        body.statement,
        methodology=body.methodology,
        created_by=operator,
        meta=body.meta,
        priority_score=body.priority_score,
    )
    return {"hypothesis_id": hid}


@app.post("/api/hypotheses/{hypothesis_id}/advance")
def advance(hypothesis_id: str):
    repo = get_repo()
    svc = ResearchService(repo)
    try:
        return svc.advance_to_awaiting_approval(hypothesis_id)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/hypotheses/{hypothesis_id}/approve-entry")
def approve_entry(hypothesis_id: str, body: ApproveBody):
    repo = get_repo()
    svc = ResearchService(repo)
    approver = body.approver_id or os.environ.get("STUDIO_OPERATOR_ID", "user-operator")
    # ensure user exists
    repo.upsert_user(approver, os.environ.get("STUDIO_OPERATOR_NAME", "Operator"))
    try:
        return svc.approve_entry(hypothesis_id, approver, note=body.note)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/hypotheses/{hypothesis_id}/search-space")
def search_space(hypothesis_id: str, body: SearchSpaceBody):
    repo = get_repo()
    svc = ResearchService(repo)
    try:
        sid = svc.define_search_space(hypothesis_id, body.definition)
        return {"search_space_id": sid}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/hypotheses/{hypothesis_id}/generate")
def generate(hypothesis_id: str, limit: int | None = None):
    repo = get_repo()
    svc = ResearchService(repo)
    try:
        n = svc.generate_candidates(hypothesis_id, limit=limit)
        return {"candidates": n}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/hypotheses/{hypothesis_id}/ladder")
def ladder(hypothesis_id: str, body: LadderBody):
    repo = get_repo()
    svc = ResearchService(repo)
    try:
        reports = svc.run_ladder(hypothesis_id, through_level=body.through_level)
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/hypotheses/{hypothesis_id}/composite")
def composite(hypothesis_id: str):
    repo = get_repo()
    svc = ResearchService(repo)
    try:
        return svc.build_assessment_and_composite(hypothesis_id)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/composites")
def composites():
    return get_repo().list_composites()


@app.get("/api/lock")
def lock():
    return get_repo().get_mvp_lock()


@app.get("/")
def index():
    index_path = DASHBOARD_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>NestQuant Studio</h1><p>Dashboard missing.</p>")
    return FileResponse(index_path)


# static assets next to index
if DASHBOARD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")


def main() -> None:
    import uvicorn

    host = os.environ.get("STUDIO_HOST", "0.0.0.0")
    port = int(os.environ.get("STUDIO_PORT", "8080"))
    uvicorn.run("nestquant_studio.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()