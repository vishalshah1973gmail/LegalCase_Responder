"""GUI 2 — Chat Bot (grounded RAG over the property-law corpus)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import cloud_bootstrap  # noqa: E402,F401  (sqlite shim + secrets; must precede config)

import streamlit as st  # noqa: E402

from config import ANTHROPIC_MODEL, DEFAULT_TOP_K, DISCLAIMER  # noqa: E402
from retrieval import store  # noqa: E402
from retrieval.export_docx import build_memo, suggested_filename  # noqa: E402
from retrieval.generate import generate_answer  # noqa: E402
from retrieval.search import filter_options, search  # noqa: E402

st.set_page_config(page_title="Chat Bot — LegalCase Responder",
                   page_icon="💬", layout="wide")

from _auth import require_password  # noqa: E402

if not require_password():
    st.stop()

st.title("💬 Chat Bot")
st.caption("Ask about riders, paragraphs and clauses. Every answer is grounded in "
           "retrieved excerpts and cited.")

# Permanent, always-visible disclaimer (also repeated in the sidebar and the export).
st.warning(DISCLAIMER)

# ------------------------------------------------------------------ guard
conn = store.connect()
stats = store.stats(conn)
conn.close()
if stats["total_chunks"] == 0:
    if cloud_bootstrap.is_read_only():
        st.error("The prebuilt index is missing from this deployment. The `db/` "
                 "folder must be committed to the repository — see the deployment "
                 "guide in the README.")
    else:
        st.error("The index is empty. Run **Data Ingestion** first.")
    st.stop()

opts = filter_options()

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Search filters")
    f_case = st.multiselect("Case", opts["case_name"])
    f_juris = st.multiselect("Jurisdiction", opts["jurisdiction"])
    f_type = st.multiselect("Case type", opts["case_type"])
    f_sect = st.multiselect("Section type", ["rider", "paragraph", "clause"])
    f_src = st.multiselect("Source", opts["source"])

    st.divider()
    st.header("Retrieval")
    top_k = st.slider("Top-k chunks", 1, 20, DEFAULT_TOP_K)
    min_score = st.slider("Minimum similarity", 0.0, 0.9, 0.15, 0.05,
                          help="Chunks scoring below this are discarded before "
                               "generation, so weak matches cannot ground an answer.")
    st.divider()
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    st.caption(f"Generation model: `{ANTHROPIC_MODEL}`")
    st.caption(("🔑 API key detected." if has_key else
                "⚠️ No `ANTHROPIC_API_KEY` — retrieval works, answer generation is off."))
    st.divider()
    st.caption(DISCLAIMER)

filters = dict(case_names=f_case, jurisdictions=f_juris, case_types=f_type,
               section_types=f_sect, sources=f_src)
filters_desc = "; ".join(
    f"{k}={v}" for k, v in
    [("case", f_case), ("jurisdiction", f_juris), ("case_type", f_type),
     ("section_type", f_sect), ("source", f_src)] if v) or "none"

# ------------------------------------------------------------------ question
EXAMPLES = [
    "What does the rider on late fees typically say in landlord-tenant cases?",
    "Find paragraphs about adverse possession boundary disputes",
    "How is 'gross sales' defined in percentage rent riders?",
    "What notice must a lender give before accelerating a mortgage?",
    "When can an HOA fine be voided?",
]
with st.expander("Example questions"):
    for e in EXAMPLES:
        st.markdown(f"- {e}")

question = st.text_area("Your question", height=90,
                        placeholder=EXAMPLES[0], key="q")
go = st.button("🔎 Search & answer", type="primary")

if go and question.strip():
    with st.spinner("Retrieving…"):
        hits = search(question, top_k=top_k, min_score=min_score, **filters)
    with st.spinner("Generating grounded answer…" if hits else "Done"):
        answer, err = generate_answer(question, hits)
    st.session_state["result"] = {"question": question, "hits": hits,
                                  "answer": answer, "err": err,
                                  "filters_desc": filters_desc}

res = st.session_state.get("result")
if res:
    hits, answer, err = res["hits"], res["answer"], res["err"]

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Answer")
        if err:
            st.error(err)
        if answer:
            st.markdown(answer)
        elif not err:
            st.info("No answer generated.")

        if hits:
            st.divider()
            docx_bytes = build_memo(res["question"], answer or "", hits,
                                    model=ANTHROPIC_MODEL,
                                    filters_desc=res["filters_desc"])
            st.download_button(
                "⬇️  Download as .docx (legal-memo format)",
                data=docx_bytes,
                file_name=suggested_filename(res["question"]),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="secondary",
            )

    with right:
        st.subheader(f"Retrieved chunks ({len(hits)})")
        if not hits:
            st.info("Nothing passed the similarity floor. Lower it or clear filters.")
        for i, h in enumerate(hits, start=1):
            m = h.meta
            badge = "🟢 REAL" if h.source == "real" else "🟠 SYNTHETIC"
            with st.expander(
                    f"{i}. {h.citation()} — {h.score:.3f}", expanded=(i <= 2)):
                st.caption(
                    f"{badge} · {m.get('court','')} · {m.get('jurisdiction','')} · "
                    f"{m.get('date','')} · case_type: `{m.get('case_type','')}` · "
                    f"section: `{h.section_type} {h.section_number}` · "
                    f"chunk_id: `{h.chunk_id}`")
                if m.get("heading"):
                    st.markdown(f"*{m['heading']}*")
                st.write(h.text)
