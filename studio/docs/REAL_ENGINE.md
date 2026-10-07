# Studio Evaluation Engine

`SimulatedExecutionAdapter` (in `engine/eval_adapter.py`) is the bridge that
turns a ladder candidate into *real* canonical metrics:

candidate params ->
  `ExecutionSimulator.open_trade/check_exits` ->
    trade list ->
      `evaluation.evaluator.evaluate` -> real metric definitions -> pass/kill

It is deterministic (candidate-seeded), so CI can assert exact metric dicts.
Production swaps this adapter for a real EvalAdapter wired to Dukascopy bars —
the ladder, repo, and approval gates are unchanged.

Cloud note: Studio's SQLite store mirrors the Postgres schema;
run with `STUDIO_DB_PATH=/path/to/studio.db` (or Postgres later) for a
persistent store.
