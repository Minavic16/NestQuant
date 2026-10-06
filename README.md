# NestQuant

Canonical monorepo for the NestQuant ecosystem.

- `nqts/` — **NestQuant Trading System**: runtime execution of validated strategies, risk/portfolio management, monitoring, notifications, MT5 connectivity.
- `studio/` — **NestQuant Studio**: research OS for validation, experiments, and candidate strategy generation.
- `contracts/` — language-neutral contracts shared by both.
- `admin-ui/` — unified operator dashboard (NQTS ops + Studio admin).

## Principles

1. Studio validates; NQTS executes. No experiments inside NQTS.
2. NQTS runs only approved, provenance-pinned artifacts from Studio.
3. Observable, modular, secure, and maintainable over clever.
4. No hardcoded paths or machine-local assumptions.

## Layout

```
nqts/production/   signals, strategy, execution, risk, portfolio, monitoring, notifications, dashboard
nqts/core/         canonical governance, architecture, contracts, data
nqts/scripts/      run-time entry points (shadow runner, replay audits)
studio/src/ …      NestQuant Studio research OS (see studio/README.md)
contracts/         shared specs
admin-ui/          unified admin dashboard (planned)
```

## Status

Migrated from `Minavic16/that` (stale) and `NestQuant-Prod`. See `docs/` for the architecture plan.
