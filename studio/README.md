# NestQuant Studio

Production-candidate **research operating system** for NestQuant.

Studio researches and validates. **NQTS** executes. **ORION** is the operator interface — not the orchestrator.

## What this is

Deterministic research infrastructure:

- Hypothesis lifecycle (state machine + append-only events)
- Search-space → mechanical candidate materialization
- Validation ladder (`strategy_ladder_v1`, L0–L5)
- Approvals (entry, composite, portfolio, NQTS export)
- Activity stream (dashboard-visible)
- Strategy Composite / RiskConstraintSet / Portfolio / Regime schemas
- Engineering task + audit verdict hooks

AI agents plug in as **slots** (reasoning / builder / tester / auditor). They do not own state, versioning, or ladder bookkeeping.

## Quick start

```bash
cd nestquant-studio
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export STUDIO_DB_PATH=./data/studio.db
python -m nestquant_studio.services.seed
pytest -q
uvicorn nestquant_studio.api.app:app --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:8080/` for the operator dashboard.

## Hard constraints (locked)

1. Studio ≠ NQTS
2. Deterministic ownership of lifecycle/state
3. Portfolio does not rewrite upstream components
4. Survivors ≠ automatic independent strategies
5. Human approval gates
6. ORION is not internal orchestrator
7. Research types keep distinct semantics
8. No architecture-for-sophistication
9. Mechanical candidate generation from search space
10. MVP: one active hypothesis; variants concurrent
11. Preserve evidence/lineage
12. Mandatory/repetitive work is software
13. NQTS only after approval
14. Prefer open-source
15. Model selection = cost per successful task

## Entities are data, not code

Domain symbols, strategies, and labels live in DB rows / JSON documents.
Seed data is generic demo only (`seed=true` in meta).

## License

Proprietary — NestQuant / Mindavic.