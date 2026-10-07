# NestQuant

Canonical monorepo for the NestQuant ecosystem.

`nqts/`   — NestQuant Trading System: validated strategy execution, risk engine,
            portfolio, monitoring, notifications, MT5 connector, shadow replay.
`studio/` — NestQuant Studio: the research OS (hypothesis lifecycle, search space,
            experiment evaluation, walk-forward validation of candidates).
`contracts/` — language-neutral contracts + parity fixtures shared by both.
`admin-ui/` — unified NQTS+Studio admin dashboard (Next.js, futuristic black/grey).

## Boundaries (enforced by tests)

1. Studio validates; NQTS executes. **NQTS must never import Studio/research.**
   Enforced by `nqts/tests/safety/test_boundary.py`.
2. NQTS runs only approved, provenance-pinned artifacts from Studio.
3. No experiments inside NQTS. Research lives in `studio/`.

## Quickstart

```bash
pip install -e "./nqts[dev]" -e "./studio[dev]"
export NESTQUANT_SKIP_LIVE_CHECK=1 NESTQUANT_SKIP_DASHBOARD_CHECK=1
pytest nqts/tests -q        # 1073 passed
pytest studio/tests -q      # 202 passed, 529 skipped (need real market data)
cd nqts/rust && cargo test  # 19 passed, fmt+clippy clean
```

## Current state

- NQTS Python suite green; Rust risk engine / account manager / monitoring
  parity-tested against Python (`contracts/fixtures/breakers.json`).
- Studio EvalAdapter drives the **real** execution simulator + evaluator
  (`SimulatedExecutionAdapter`), deterministic for CI.
- CI: nqts (full pytest) + studio (ruff+pytest) + rust (fmt/clippy/test).
- See `docs/DECISIONS.md` for what still needs a human decision / data / VPS.
