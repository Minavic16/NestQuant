# NestQuant Studio architecture (production candidate v0.1)

## Boundaries

- **Studio** — research OS (this repo)
- **NQTS** — execution VPS (separate; receives approved exports only)
- **ORION** — operator interface (read + approval calls; not orchestrator)

## Deterministic core

| Module | Role |
|--------|------|
| `core/state_machine.py` | Hypothesis transitions + approval gates |
| `core/search_space.py` | Mechanical candidate materialization + stable keys |
| `engine/ladder_runner.py` | L0–L5 promotion/kill bookkeeping |
| `engine/eval_adapter.py` | Pluggable eval interface (toy adapter for tests) |
| `db/repo.py` | System of record + `activity_event` stream |
| `services/research.py` | Lifecycle orchestration |
| `api/app.py` | HTTP API + dashboard static host |

## Data

SQLite by default (`STUDIO_DB_PATH`). Schema in `schemas/studio_schema_v1.sql` mirrors the Postgres-oriented design.

Domain entities (symbols, live strategies, accounts) are **not** hardcoded in Python modules. They enter via JSON search spaces, eval configs, and DB documents.

## Dashboard

Operator monitor at `/` — black base, textured grey surfaces — shows KPIs, hypotheses, activity stream, ladder runs, engineering tasks, composites.

## Suggested additions (not yet built)

1. Postgres backend + migration tool (Alembic)
2. Redis job queue for concurrent variant evals
3. Content-addressed blob store for evidence packs
4. Real backtester `EvalAdapter`
5. Signed NQTS export package builder
6. ORION-facing read-only token auth
7. WebSocket activity push
8. Purged/walk-forward CV utilities for regime research