# Decisions & owner-required items

## D1 — Prop-firm guard calibration (NEEDS OWNER DECISION)

Three tests are `xfail(strict=True)` because the prop-firm guard's defaults drifted
over the migration. Current policy (`core/configuration/constitution.py`):
0.15%/trade, 3% daily loss, 8% total drawdown, 3 positions, 3.0 total exposure.
AGENTS.md §468 agrees (0.15%/trade, 3% daily). The rejected tests asserted the
older 1%/trade + $8,000-on-$200k daily limit.

Resolution options: (a) keep the constitution, rewrite the 3 tests to the new
values; (b) revert the constitution. Both sides of the fork are otherwise green.
The strict xfail will flip CI red the moment someone "fixes" either side —
which is the forcing function for a decision.

## D2 — Market data for legacy research tests (NEEDS DATA)

`Studio` research tests gate on `data_dir()` containing the FX pickles and
`research/output/` containing the experiment JSONs. When `STUDIO_DATA_DIR`
exposes them, they run; otherwise they skip with the explicit reason.

## D3 — Postgres for Studio (not started; additive)

Studio's store is SQLite; schema mirrors the Postgres design in
`studio/schemas/studio_schema_v1.sql`. Alembic/manager can be added without
changing the repository interface.

## D4 — Rust sidecars are parity-tested, not yet a service

`nqts/rust` passes `fmt`/`clippy -D warnings`/`cargo test` and its breakers are
fixture-parity-tested against Python. They are not yet wired as a running
service / replacing the Python guard in the shadow runner (Phase 3 continues).

## D5 — Deploy workflow is gated off

`.github/workflows/deploy.yml`'s `deploy` job is `if: false` until a VPS runner
with deploy secrets is attached. The build job runs in CI.
