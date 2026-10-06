"""
Runtime configuration — single source of truth for machine-local paths and
secrets.  Every value is overridable via environment variable; sensible
defaults are derived from the repository root (no machine-specific paths).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[3]


def _env_path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v).expanduser() if v else default


@dataclass(frozen=True)
class RuntimeConfig:
    # Repository roots
    repo_root: Path = _ROOT
    data_dir: Path = field(default_factory=lambda: _env_path("NQTS_DATA_DIR", _ROOT / "data"))
    log_dir: Path = field(default_factory=lambda: _env_path("NQTS_LOG_DIR", _ROOT / "logs"))
    accounts_yaml: Path = field(default_factory=lambda: _env_path("ACCOUNTS_YAML", _ROOT / "accounts.yaml"))
    mt5_path: Optional[str] = field(default_factory=lambda: os.getenv("MT5_PATH") or None)

    # Dashboard
    dashboard_host: str = field(default_factory=lambda: os.getenv("DASHBOARD_HOST", "0.0.0.0"))
    dashboard_port: int = field(default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "8080")))
    dashboard_secret: str = field(default_factory=lambda: os.getenv("DASHBOARD_SECRET", ""))

    # Notifications / alerting
    alert_enabled: bool = field(default_factory=lambda: os.getenv("ALERT_ENABLED", "true").lower() == "true")
    alert_webhook_url: str = field(default_factory=lambda: os.getenv("ALERT_WEBHOOK_URL", ""))
    alert_webhook_type: str = field(default_factory=lambda: os.getenv("ALERT_WEBHOOK_TYPE", "ntfy"))
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # Data / news
    news_csv_path: Optional[str] = field(default_factory=lambda: os.getenv("NEWS_CSV_PATH") or None)

    # Accounts
    accounts_yaml_str: str = field(default_factory=lambda: os.getenv("ACCOUNTS_YAML", str(_ROOT / "accounts.yaml")))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    json_logs: bool = field(default_factory=lambda: os.getenv("NQTS_JSON_LOGS", "false").lower() == "true")


_config: Optional[RuntimeConfig] = None


def get_runtime() -> RuntimeConfig:
    global _config
    if _config is None:
        _config = RuntimeConfig()
    return _config
