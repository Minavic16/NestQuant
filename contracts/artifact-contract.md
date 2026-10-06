# Promotion Artifact Contract v1

Studio produces only immutable artifacts. NQTS runs only artifacts that:

1. Have a `strategy_id` + `version`, and a `provenance_hash` (SHA of the
   exact source commit + params + evaluator version + metrics).
2. Carry a `risk_constraint_set` and a `portfolio_declaration`.
3. Are explicitly approved (`HUMAN_APPROVED`) by the operator.

NQTS startup must refuse to boot on unapproved or unpinned artifacts.
