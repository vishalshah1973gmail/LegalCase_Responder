"""LegalCase Responder — Streamlit entry point.

Run from the project root:  streamlit run app/Home.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cloud_bootstrap  # noqa: E402,F401  (sqlite shim + secrets; must precede config)

import streamlit as st  # noqa: E402
from config import (ANTHROPIC_MODEL, CASES_DIR, CHROMA_DIR, DISCLAIMER,  # noqa: E402
                    EMBEDDING_MODEL, SQLITE_PATH)
from retrieval import store  # noqa: E402

st.set_page_config(page_title="LegalCase Responder", page_icon="⚖️", layout="wide")

from _auth import require_password  # noqa: E402

if not require_password():
    st.stop()

st.title("⚖️ LegalCase Responder")
st.caption("Retrieval-augmented lookup of riders, paragraphs and clauses across a "
           "property-law case corpus.")

st.warning(DISCLAIMER)

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("How to use this app")
    st.markdown(
        """
1. **Data Ingestion** (page 1) — build the index. Chunks the corpus one
   rider / paragraph / clause at a time, embeds each chunk locally, and stores
   vectors in ChromaDB and metadata in SQLite. Safe to re-run: unchanged cases
   are skipped, changed cases are upserted.
2. **Chat Bot** (page 2) — ask a question, optionally filtered by case,
   jurisdiction or case type. You see the retrieved chunks next to the answer,
   and can export any answer as a legal-memo `.docx`.

Retrieval works with **no API key**. A key is needed only for the answer-writing step.
        """
    )

with col2:
    st.subheader("Index status")
    n_files = len(list(CASES_DIR.glob("*.json")))
    try:
        conn = store.connect()
        s = store.stats(conn)
        conn.close()
    except Exception as exc:
        s = {"total_cases": 0, "total_chunks": 0, "by_source": {}}
        st.error(f"Store unavailable: {exc}")

    a, b, c = st.columns(3)
    a.metric("Corpus files", n_files)
    b.metric("Cases indexed", s["total_cases"])
    c.metric("Chunks indexed", s["total_chunks"])
    if s.get("by_source"):
        st.write("**By source:** " + " · ".join(
            f"{k}: {v}" for k, v in sorted(s["by_source"].items())))
    if s["total_chunks"] == 0:
        st.info("Nothing indexed yet — start on the **Data Ingestion** page.")

with st.expander("Configuration"):
    st.write(f"**Embedding model** (local, free): `{EMBEDDING_MODEL}`")
    st.write(f"**Generation model**: `{ANTHROPIC_MODEL}` "
             f"(set `ANTHROPIC_MODEL` in `.env` to change)")
    st.write(f"**Chroma path**: `{CHROMA_DIR}`")
    st.write(f"**SQLite path**: `{SQLITE_PATH}`")
    st.write(f"**Corpus path**: `{CASES_DIR}`")
    st.write(f"**sqlite3**: {cloud_bootstrap.SQLITE_STATUS}")
    st.write(f"**Secrets**: {cloud_bootstrap.SECRETS_STATUS}")

    import os as _os
    if (_os.getenv("APP_PASSWORD") or "").strip():
        st.write("**Access**: 🔒 password gate ON (`APP_PASSWORD` is set)")
    else:
        st.write("**Access**: 🔓 password gate OFF — no `APP_PASSWORD` set, so the "
                 "app is open. That is the intended default for local use. Set "
                 "`APP_PASSWORD` in `.env` (local) or in Streamlit **Secrets** "
                 "(deployed) to require one. **Set it before you deploy** — a "
                 "public URL bills your Anthropic key on every question.")
    if cloud_bootstrap.is_read_only():
        st.write("**Mode**: read-only (ingestion disabled — deployed build)")
