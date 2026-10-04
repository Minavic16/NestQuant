from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "studio_schema_v1.sql"


def db_path() -> Path:
    p = os.environ.get("STUDIO_DB_PATH", "").strip()
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[3] / "data" / "studio.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()