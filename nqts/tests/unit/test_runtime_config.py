"""RuntimeConfig is the single source of truth for machine-local paths."""
import subprocess
import sys
import textwrap


def _run(code: str, **env) -> str:
    import os
    full = {**os.environ, **env}
    for k in ("NQTS_DATA_DIR", "NQTS_LOG_DIR", "ACCOUNTS_YAML"):
        if k not in env:
            full.pop(k, None)
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)],
                          capture_output=True, text=True, env=full, check=True).stdout.strip()


def test_settings_and_runtime_agree_by_default():
    out = _run("""
        from nestquant.core.configuration.runtime import get_runtime
        from nestquant.core.configuration.settings import get_config
        print(get_runtime().data_dir == __import__('pathlib').Path(get_config().data.data_dir))
    """)
    assert out == "True"


def test_env_override_reaches_loader_and_settings(tmp_path):
    out = _run("""
        from nestquant.core.configuration.settings import get_config, DATA_DIR
        from nestquant.core.data.loader import DataLoader
        print(get_config().data.data_dir, DATA_DIR, DataLoader().data_dir)
    """, NQTS_DATA_DIR=str(tmp_path))
    assert out.split() == [str(tmp_path)] * 3


def test_no_machine_specific_defaults():
    out = _run("""
        from nestquant.core.configuration.runtime import get_runtime
        r = get_runtime()
        print(any(str(p).startswith('/root') for p in (r.data_dir, r.log_dir, r.accounts_yaml)))
    """)
    # Defaults derive from the checkout location, never a hardcoded /root path.
    # (Skip the assertion when the checkout itself lives under /root.)
    import nestquant
    if not str(nestquant.__file__).startswith("/root"):
        assert out == "False"
