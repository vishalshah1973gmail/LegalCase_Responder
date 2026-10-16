"""GUI 1 — Data Ingestion."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import cloud_bootstrap  # noqa: E402,F401  (sqlite shim + secrets; must precede config)

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from config import (CASES_DIR, DEFAULT_CHUNK_OVERLAP_CHARS,  # noqa: E402
                    DEFAULT_MAX_CHUNK_CHARS, DISCLAIMER, EMBEDDING_MODEL)
from ingestion.ingest import ingest, load_corpus  # noqa: E402
from retrieval import store  # noqa: E402

st.set_page_config(page_title="Data Ingestion — LegalCase Responder",
                   page_icon="📥", layout="wide")

from _auth import require_password  # noqa: E402

if not require_password():
    st.stop()

READ_ONLY = cloud_bootstrap.is_read_only()

st.title("📥 Data Ingestion")
st.caption("Chunk → embed → ChromaDB (vectors) + SQLite (metadata)")
st.warning(DISCLAIMER)

if READ_ONLY:
    st.info(
        "**Read-only deployment.** This app is running on a host with an ephemeral "
        "filesystem, so the index is prebuilt and shipped with the repository — "
        "re-ingesting here would be lost on the next reboot and would blow the "
        "memory budget. The controls below are disabled. Clone the repo and run "
        "locally to re-ingest.",
        icon="🔒")

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Chunking configuration")
    st.markdown("Default boundary is **one rider / paragraph / clause per chunk**. "
                "A section longer than the limit below is split further, with overlap.")
    max_chars = st.slider("Max characters per chunk", 400, 6000,
                          DEFAULT_MAX_CHUNK_CHARS, step=100)
    overlap = st.slider("Overlap for split sections (chars)", 0, 800,
                        DEFAULT_CHUNK_OVERLAP_CHARS, step=25)
    st.caption(f"≈ {max_chars // 4} tokens per chunk at ~4 chars/token.")
    st.divider()
    force = st.checkbox("Force re-embed every case", value=False,
                        help="Ignore the skip-if-unchanged check.")
    st.caption(f"Embedding model: `{EMBEDDING_MODEL}` (local, free, offline "
               f"after the first download).")
    try:
        from retrieval.embedder import _choose_backend
        st.caption(f"Backend: `{_choose_backend()}`")
    except Exception:
        pass

# ------------------------------------------------------------------ corpus preview
files = sorted(CASES_DIR.glob("*.json"))
st.subheader("1 · Corpus on disk")
if not files:
    st.error(f"No case files found in `{CASES_DIR}`.")
    st.code("python ingestion/corpus_builder.py -n 120", language="bash")
    st.stop()

cases = load_corpus()
prev = pd.DataFrame([{
    "case_id": c["case_id"], "case_name": c["case_name"],
    "case_type": c.get("case_type", ""), "jurisdiction": c.get("jurisdiction", ""),
    "date": c.get("date", ""), "source": c.get("source", ""),
    "sections": len(c.get("sections", [])),
} for c in cases])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Case files", len(files))
c2.metric("Sections total", int(prev["sections"].sum()))
c3.metric("Real", int((prev["source"] == "real").sum()))
c4.metric("Synthetic", int((prev["source"] == "synthetic").sum()))
with st.expander("Preview the corpus manifest"):
    st.dataframe(prev, use_container_width=True, height=280)

# ------------------------------------------------------------------ run
st.subheader("2 · Run ingestion")
b1, b2 = st.columns([1, 3])
run = b1.button("▶️  Ingest corpus", type="primary", use_container_width=True,
                disabled=READ_ONLY)
if b2.button("🗑️  Reset both stores (wipe index)", use_container_width=False,
             disabled=READ_ONLY):
    store.reset_all()
    st.success("Chroma collection and SQLite tables cleared.")
    st.rerun()

if run and not READ_ONLY:
    progress = st.progress(0.0, text="Starting…")
    log_box = st.empty()
    lines: list[str] = []
    t0 = time.time()

    def log(msg: str) -> None:
        lines.append(msg)
        log_box.code("\n".join(lines[-18:]), language=None)

    def on_progress(frac: float, msg: str) -> None:
        progress.progress(min(frac, 1.0), text=msg[:110])

    with st.spinner("Embedding and indexing…"):
        summary = ingest(cases=cases, max_chars=max_chars, overlap=overlap,
                         log=log, progress=on_progress, force=force)
    progress.progress(1.0, text="Complete")
    st.success(
        f"Ingested {summary['cases_ingested']} case(s), skipped "
        f"{summary['cases_skipped']} already-current case(s), wrote "
        f"{summary['chunks_written']} chunk(s) in {time.time() - t0:.1f}s."
    )
    st.session_state["last_ingest_log"] = lines

if "last_ingest_log" in st.session_state:
    with st.expander("Full log from the last run"):
        st.code("\n".join(st.session_state["last_ingest_log"]), language=None)

# ------------------------------------------------------------------ stats
st.subheader("3 · Index summary")
conn = store.connect()
s = store.stats(conn)
conn.close()

if s["total_chunks"] == 0:
    st.info("Index is empty. Run ingestion above.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cases indexed", s["total_cases"])
    m2.metric("Chunks indexed", s["total_chunks"])
    m3.metric("Real cases", s["by_source"].get("real", 0))
    m4.metric("Synthetic cases", s["by_source"].get("synthetic", 0))

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Cases by case type**")
        df = pd.DataFrame(sorted(s["by_case_type"].items()),
                          columns=["case_type", "cases"]).set_index("case_type")
        st.bar_chart(df, height=260)
    with g2:
        st.markdown("**Chunks by section type**")
        df2 = pd.DataFrame(sorted(s["chunks_by_section_type"].items()),
                           columns=["section_type", "chunks"]).set_index("section_type")
        st.bar_chart(df2, height=260)

    j1, j2 = st.columns(2)
    with j1:
        st.markdown("**Chunks by source**")
        st.dataframe(pd.DataFrame(sorted(s["chunks_by_source"].items()),
                                  columns=["source", "chunks"]),
                     use_container_width=True, hide_index=True)
    with j2:
        st.markdown("**Cases by jurisdiction**")
        st.dataframe(pd.DataFrame(sorted(s["by_jurisdiction"].items()),
                                  columns=["jurisdiction", "cases"]),
                     use_container_width=True, hide_index=True, height=240)
