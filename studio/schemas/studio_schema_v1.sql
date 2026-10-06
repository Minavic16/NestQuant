-- NestQuant Studio schema v1 (SQLite production-candidate; Postgres-ready shapes)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_user (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT UNIQUE,
  role TEXT NOT NULL DEFAULT 'operator',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS evidence_blob (
  sha256 TEXT PRIMARY KEY,
  size_bytes INTEGER NOT NULL,
  content_type TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ladder_def (
  ladder_id TEXT PRIMARY KEY,
  research_type TEXT NOT NULL,
  document TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_space (
  search_space_id TEXT PRIMARY KEY,
  definition TEXT NOT NULL,
  definition_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hypothesis (
  hypothesis_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  methodology TEXT,
  status TEXT NOT NULL DEFAULT 'discovered',
  priority_score REAL,
  academic_support TEXT,
  eligibility TEXT,
  search_space_id TEXT REFERENCES search_space(search_space_id),
  ladder_id TEXT REFERENCES ladder_def(ladder_id),
  parent_hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
  meta TEXT,
  created_by TEXT REFERENCES app_user(user_id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hypothesis_event (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  hypothesis_id TEXT NOT NULL REFERENCES hypothesis(hypothesis_id),
  from_status TEXT,
  to_status TEXT NOT NULL,
  reason TEXT,
  actor TEXT NOT NULL,
  payload TEXT,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hypothesis_lock (
  lock_name TEXT PRIMARY KEY DEFAULT 'mvp_active',
  hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
  held_since TEXT
);

CREATE TABLE IF NOT EXISTS candidate (
  candidate_id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES hypothesis(hypothesis_id),
  candidate_key TEXT NOT NULL,
  params TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'generated',
  kill_reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (hypothesis_id, candidate_key)
);

CREATE INDEX IF NOT EXISTS candidate_hyp_status_idx ON candidate (hypothesis_id, status);

CREATE TABLE IF NOT EXISTS candidate_event (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL REFERENCES candidate(candidate_id),
  from_status TEXT,
  to_status TEXT NOT NULL,
  level_id TEXT,
  reason TEXT,
  metrics TEXT,
  evidence_sha256 TEXT REFERENCES evidence_blob(sha256),
  actor TEXT NOT NULL,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ladder_level_run (
  run_id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES hypothesis(hypothesis_id),
  ladder_id TEXT NOT NULL REFERENCES ladder_def(ladder_id),
  level_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  cost TEXT,
  report TEXT,
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS level_candidate_result (
  run_id TEXT NOT NULL REFERENCES ladder_level_run(run_id),
  candidate_id TEXT NOT NULL REFERENCES candidate(candidate_id),
  level_id TEXT NOT NULL,
  passed INTEGER NOT NULL,
  metrics TEXT,
  kill_reason TEXT,
  evidence_sha256 TEXT REFERENCES evidence_blob(sha256),
  PRIMARY KEY (run_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS eval_config (
  eval_config_id TEXT PRIMARY KEY,
  research_type TEXT NOT NULL,
  level_id TEXT,
  document TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assessment_profile (
  profile_id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES hypothesis(hypothesis_id),
  body TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS strategy_composite (
  composite_id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  body TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (composite_id, version)
);

CREATE TABLE IF NOT EXISTS risk_constraint_set (
  rcs_id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  body TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (rcs_id, version)
);

CREATE TABLE IF NOT EXISTS regime_model (
  regime_model_id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  body TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (regime_model_id, version)
);

CREATE TABLE IF NOT EXISTS portfolio_declaration (
  portfolio_id TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'proposed',
  body TEXT NOT NULL,
  body_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (portfolio_id, version)
);

CREATE TABLE IF NOT EXISTS component_registry (
  component_id TEXT PRIMARY KEY,
  component_type TEXT NOT NULL,
  ref_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  status TEXT NOT NULL,
  registered_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (component_type, ref_id, version)
);

CREATE TABLE IF NOT EXISTS approval (
  approval_id TEXT PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  subject_version INTEGER,
  subject_hash TEXT NOT NULL,
  approver_id TEXT NOT NULL REFERENCES app_user(user_id),
  note TEXT,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS engineering_task (
  task_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  contract TEXT NOT NULL,
  git_branch TEXT,
  git_commit TEXT,
  result TEXT,
  cost TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_verdict (
  verdict_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES engineering_task(task_id),
  verdict TEXT NOT NULL,
  findings TEXT,
  auditor TEXT NOT NULL,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_ledger (
  entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_kind TEXT NOT NULL,
  job_ref TEXT,
  hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
  usd REAL DEFAULT 0,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cpu_seconds REAL DEFAULT 0,
  meta TEXT,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS job (
  job_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS activity_event (
  activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'info',
  title TEXT NOT NULL,
  detail TEXT,
  entity_type TEXT,
  entity_id TEXT,
  hypothesis_id TEXT,
  actor TEXT,
  payload TEXT,
  at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS activity_at_idx ON activity_event (at DESC);
CREATE INDEX IF NOT EXISTS activity_hyp_idx ON activity_event (hypothesis_id);