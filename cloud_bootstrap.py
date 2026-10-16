"""Run this FIRST, before importing config / chromadb / anything else.

Two jobs, both no-ops on a normal local machine:

1. **sqlite3 shim.** Streamlit Community Cloud's Debian image ships an sqlite3
   older than the 3.35 that ChromaDB requires. If `pysqlite3-binary` is
   installed and the stdlib version is too old, we transparently swap it in.
2. **Secrets bridge.** Streamlit Cloud supplies secrets via `st.secrets`, not a
   `.env` file. Anything defined there is copied into `os.environ` so the rest
   of the codebase can keep using plain `os.getenv`.

Import it at the very top of every Streamlit page:

    import cloud_bootstrap  # noqa: F401  (must precede `import config`)
"""
from __future__ import annotations

import os
import sys

# ------------------------------------------------------------------ 1. sqlite3
def _patch_sqlite() -> str:
    import sqlite3 as _std
    if tuple(int(x) for x in _std.sqlite_version.split(".")[:3]) >= (3, 35, 0):
        return f"stdlib sqlite3 {_std.sqlite_version} (no shim needed)"
    try:
        import pysqlite3  # noqa: F401
    except ImportError:
        return (f"stdlib sqlite3 {_std.sqlite_version} is too old for ChromaDB "
                f"(needs >= 3.35) and pysqlite3-binary is not installed")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    sys.modules["sqlite3.dbapi2"] = sys.modules["sqlite3"].dbapi2
    return f"swapped in pysqlite3 {sys.modules['sqlite3'].sqlite_version}"


SQLITE_STATUS = _patch_sqlite()


# ------------------------------------------------------------------ 2. secrets
def _load_secrets() -> str:
    """Copy st.secrets into os.environ. Existing env vars win (local .env)."""
    try:
        import streamlit as st
        secrets = st.secrets
    except Exception:
        return "no Streamlit secrets available"
    loaded = []
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_MAX_TOKENS",
                "EMBEDDING_MODEL", "EMBEDDING_BACKEND", "APP_PASSWORD",
                "READ_ONLY", "COURTLISTENER_TOKEN"):
        try:
            val = secrets[key]
        except Exception:
            continue
        if val and not os.getenv(key):
            os.environ[key] = str(val)
            loaded.append(key)
    return f"loaded from st.secrets: {', '.join(loaded)}" if loaded else "no secrets set"


SECRETS_STATUS = _load_secrets()


def is_read_only() -> bool:
    """True when the deployment should refuse writes (ephemeral cloud disk)."""
    return os.getenv("READ_ONLY", "").strip().lower() in ("1", "true", "yes")
