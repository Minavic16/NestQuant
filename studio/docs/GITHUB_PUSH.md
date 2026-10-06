# GitHub Push Notes (historical)

> These are the notes from the original v0.1 push attempt. The canonical
> NestQuant monorepo is `Minavic16/NestQuant` (renamed from
> `NestQuant-Prod`, migrated from `Minavic16/that`).

## What happened originally

- Push failed because the PromptQL GitHub App had 0 installations, and the
  PAT-based push returned 403 (`Permission denied`).
- Those issues have since been resolved: the repo was renamed to
  `NestQuant`, source was committed via the local git remote, and CI was added.

## Rules now

1. Never commit a saved page snapshot (the old `NestQuant-Studio [Codespaces]`
   HTML is not source). Use `git clone --depth` for speed.
2. Experiments belong in `studio/`; NQTS runtime belongs in `nqts/`.
3. CI (`.github/workflows/ci.yml`) must stay green: Studio tests + NQTS unit/smoke.
