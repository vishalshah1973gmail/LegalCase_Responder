"""End-to-end smoke test — runs fully offline.

If chromadb / sentence-transformers are installed, the REAL drivers are used.
If they are not (e.g. an air-gapped machine), the stubs in tests/stubs are used
instead, so the pipeline logic can still be verified. Run:

    python tests/smoke_test.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

USING_STUBS = importlib.util.find_spec("chromadb") is None
if USING_STUBS:
    sys.path.insert(0, str(Path(__file__).parent / "stubs"))

# Point the stores at a scratch directory so the real db/ is untouched.
TMP = Path(tempfile.mkdtemp(prefix="lcr-smoke-"))
import config  # noqa: E402
config.DB_DIR = TMP
config.CHROMA_DIR = TMP / "chroma"
config.SQLITE_PATH = TMP / "metadata.sqlite"
config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)

from ingestion import ingest as ingest_mod  # noqa: E402
from ingestion.chunker import chunk_case  # noqa: E402
from ingestion.corpus_builder import build_case  # noqa: E402
from retrieval import search as search_mod, store  # noqa: E402
from retrieval.export_docx import build_memo, suggested_filename  # noqa: E402
from retrieval.generate import build_user_message, NO_CONTEXT_MSG, generate_answer  # noqa: E402

store.CHROMA_DIR = config.CHROMA_DIR
store.SQLITE_PATH = config.SQLITE_PATH

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))


def main() -> int:
    print(f"\nSmoke test — drivers: {'STUBS (offline)' if USING_STUBS else 'REAL'}")
    print(f"scratch: {TMP}\n")

    # ---------------------------------------------------------- 1. corpus
    print("1. Corpus")
    cases = ingest_mod.load_corpus()
    check("corpus has >= 100 cases", len(cases) >= 100, f"{len(cases)}")
    check("every case has a case_id, name and sections",
          all(c.get("case_id") and c.get("case_name") and c.get("sections") for c in cases))
    check("every case tagged source real|synthetic",
          all(c.get("source") in ("real", "synthetic") for c in cases))
    sec_types = {s["section_type"] for c in cases for s in c["sections"]}
    check("section types are rider/paragraph/clause",
          sec_types <= {"rider", "paragraph", "clause"}, str(sorted(sec_types)))
    check("every case has at least one rider",
          all(any(s["section_type"] == "rider" for s in c["sections"]) for c in cases))
    check("ordered sections (contiguous order values)",
          all([s["order"] for s in c["sections"]] == list(range(1, len(c["sections"]) + 1))
              for c in cases))
    ctypes = {c["case_type"] for c in cases}
    check("multiple property-law case types", len(ctypes) >= 8, f"{len(ctypes)} types")

    # ---------------------------------------------------------- 2. chunker
    print("\n2. Chunking")
    big = build_case(0, __import__("random").Random(7))
    big["sections"][0]["text"] = "Sentence about easements. " * 400
    ch = chunk_case(big, max_chars=800, overlap=100)
    check("oversized section is split", any(c.n_parts > 1 for c in ch))
    check("no chunk exceeds max_chars", all(len(c.text) <= 800 for c in ch),
          f"max={max(len(c.text) for c in ch)}")
    check("split chunks overlap", ch[0].text[-50:] in ch[1].text if ch[1].part == 1 else True)
    check("chunk ids unique", len({c.chunk_id for c in ch}) == len(ch))
    normal = chunk_case(big, max_chars=100000, overlap=0)
    check("default granularity = one section per chunk",
          len(normal) == len(big["sections"]))

    # ---------------------------------------------------------- 3. ingestion
    print("\n3. Ingestion")
    # sample across case types (files sort by type, so a head slice would not)
    subset = [c for i, c in enumerate(sorted(cases, key=lambda c: (c["case_id"][-4:])))
              if i < 24]
    s1 = ingest_mod.ingest(cases=subset, log=lambda m: None)
    check("all cases ingested", s1["cases_ingested"] == len(subset), str(s1["cases_ingested"]))
    check("chunks written", s1["chunks_written"] > 0, str(s1["chunks_written"]))
    check("sqlite case count matches", s1["total_cases"] == len(subset))
    check("stats broken down by source", bool(s1["by_source"]), str(s1["by_source"]))
    check("stats broken down by case_type", len(s1["by_case_type"]) >= 5,
          f"{len(s1['by_case_type'])} types")

    s2 = ingest_mod.ingest(cases=subset, log=lambda m: None)
    check("re-ingest skips unchanged cases", s2["cases_skipped"] == len(subset))
    check("re-ingest creates no duplicates", s2["total_chunks"] == s1["total_chunks"],
          f"{s1['total_chunks']} -> {s2['total_chunks']}")

    edited = json.loads(json.dumps(subset[0]))
    edited["sections"][0]["text"] += " Additional appended holding on riparian rights."
    s3 = ingest_mod.ingest(cases=[edited], log=lambda m: None)
    check("changed case is upserted, not duplicated",
          s3["cases_ingested"] == 1 and s3["total_cases"] == len(subset))
    check("chunk count stays stable after upsert",
          s3["total_chunks"] == s1["total_chunks"], str(s3["total_chunks"]))

    # ---------------------------------------------------------- 4. retrieval
    print("\n4. Retrieval")
    hits = search_mod.search("late fee rider landlord tenant charge", top_k=6)
    check("search returns hits", len(hits) > 0, f"{len(hits)}")
    check("hits are descending by score",
          all(hits[i].score >= hits[i + 1].score for i in range(len(hits) - 1)))
    check("hits carry citation metadata",
          all(h.case_name and h.section_type and h.section_number for h in hits))
    check("citation never doubles the section label",
          not any(c.lower().count("rider") > 1 or c.lower().count("clause") > 1
                  for c in (h.citation() for h in
                            search_mod.search("rider clause", top_k=12))))
    check("citation string is well formed",
          all(("Rider" in h.citation() or "para." in h.citation()
               or "Clause" in h.citation()) for h in hits), hits[0].citation())

    only_riders = search_mod.search("late fee", top_k=8, section_types=["rider"])
    check("section_type filter honoured",
          all(h.section_type == "rider" for h in only_riders), f"{len(only_riders)} hits")
    a_type = subset[0]["case_type"]
    tf = search_mod.search("property", top_k=8, case_types=[a_type])
    check("case_type filter honoured",
          all(h.meta["case_type"] == a_type for h in tf), f"{len(tf)} hits")
    juris = subset[0]["jurisdiction"]
    jf = search_mod.search("property", top_k=8, jurisdictions=[juris])
    check("jurisdiction filter honoured",
          all(h.meta["jurisdiction"] == juris for h in jf), f"{len(jf)} hits")
    cf = search_mod.search("property", top_k=8, case_names=[subset[0]["case_name"]],
                           sources=["synthetic"])
    check("combined multi-field filter honoured",
          all(h.case_name == subset[0]["case_name"] and h.source == "synthetic" for h in cf))
    check("similarity floor discards weak matches",
          len(search_mod.search("late fee", top_k=8, min_score=0.999)) == 0)
    opts = search_mod.filter_options()
    check("filter option lists populated",
          all(opts[k] for k in ("case_name", "jurisdiction", "case_type", "source")))

    # ---------------------------------------------------------- 5. generation
    print("\n5. Grounded generation")
    msg = build_user_message("What do late-fee riders say?", hits)
    check("prompt embeds every retrieved excerpt", msg.count("<excerpt") == len(hits))
    check("prompt carries cite_as for each excerpt", msg.count("cite_as:") == len(hits))
    check("prompt carries the source tag", "source: synthetic" in msg)
    ans, err = generate_answer("anything", [])
    check("empty retrieval refuses to generate", ans == NO_CONTEXT_MSG and err is None)
    import os
    if not os.getenv("ANTHROPIC_API_KEY"):
        a2, e2 = generate_answer("q", hits)
        check("missing API key is reported, not crashed", a2 == "" and "ANTHROPIC_API_KEY" in (e2 or ""))
    else:
        a2, e2 = generate_answer("What do late-fee riders in this corpus say?", hits)
        check("live Claude call returned an answer", bool(a2) and e2 is None, (e2 or "")[:80])
        check("answer contains a citation", any(h.case_name.split()[0] in a2 for h in hits))

    # ---------------------------------------------------------- 6. docx
    print("\n6. Docx export")
    blob = build_memo("What does the rider on late fees say?",
                      "Late fees are capped at five percent (Example v. Case, Rider A).",
                      hits, model="claude-sonnet-5", filters_desc="section_type=['rider']")
    check("docx bytes produced", len(blob) > 5000, f"{len(blob)} bytes")
    check("is a real zip/docx container", blob[:2] == b"PK")
    out = TMP / "memo.docx"
    out.write_bytes(blob)
    try:
        from docx import Document
        d = Document(str(out))
        text = "\n".join(p.text for p in d.paragraphs)
        check("memo has the heading", "RESEARCH MEMORANDUM" in text)
        check("memo has Question Presented", "Question Presented" in text)
        check("memo has Answer section", "Answer" in text)
        check("memo has Sources section", "Sources" in text)
        check("memo lists every cited excerpt",
              all(h.citation() in text for h in hits))
        check("memo carries the not-legal-advice disclaimer",
              "not legal advice" in text.lower())
        check("memo shows source tags", "source: SYNTHETIC" in text)
    except ImportError:
        check("python-docx available to verify memo", False, "not installed")
    check("filename slug is safe",
          suggested_filename("What's the rider?! ").endswith(".docx"))

    # ---------------------------------------------------------- 7. schema
    print("\n7. Metadata schema")
    conn = store.connect()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chunks)")}
    required = {"chroma_chunk_id", "case_id", "case_name", "court", "jurisdiction",
                "date", "case_type", "source", "section_type", "section_number"}
    check("chunks table has every required column", required <= cols,
          str(sorted(required - cols)))
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(cases)")}
    check("cases table has case-level metadata",
          {"case_id", "case_name", "court", "jurisdiction", "date", "case_type",
           "source"} <= ccols)
    row = conn.execute("SELECT * FROM chunks LIMIT 1").fetchone()
    check("chroma_chunk_id links sqlite -> chroma",
          store.collection().count() > 0 and row["chroma_chunk_id"] is not None)
    n_rows = conn.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
    check("sqlite chunk count == chroma vector count",
          n_rows == store.collection().count(), f"{n_rows} vs {store.collection().count()}")
    conn.close()

    # ---------------------------------------------------------- 8. deployment
    print("\n8. Deployment readiness")
    import cloud_bootstrap
    check("sqlite3 shim reports a usable version",
          "no shim needed" in cloud_bootstrap.SQLITE_STATUS
          or "swapped in" in cloud_bootstrap.SQLITE_STATUS,
          cloud_bootstrap.SQLITE_STATUS)
    import sqlite3 as _sq
    check("effective sqlite3 >= 3.35 (ChromaDB requirement)",
          tuple(int(x) for x in _sq.sqlite_version.split(".")[:3]) >= (3, 35, 0),
          _sq.sqlite_version)
    os.environ["READ_ONLY"] = "true"
    check("READ_ONLY flag is honoured", cloud_bootstrap.is_read_only())
    os.environ.pop("READ_ONLY")
    check("READ_ONLY defaults off", not cloud_bootstrap.is_read_only())

    from retrieval.embedder import _choose_backend
    prev = os.environ.get("EMBEDDING_BACKEND")
    os.environ["EMBEDDING_BACKEND"] = "onnx"
    check("EMBEDDING_BACKEND=onnx selects onnx", _choose_backend() == "onnx")
    os.environ["EMBEDDING_BACKEND"] = "sentence-transformers"
    check("EMBEDDING_BACKEND=sentence-transformers is honoured",
          _choose_backend() == "sentence-transformers")
    os.environ["EMBEDDING_BACKEND"] = "auto"
    check("auto resolves to an available backend",
          _choose_backend() in ("onnx", "sentence-transformers"), _choose_backend())
    if prev is None:
        os.environ.pop("EMBEDDING_BACKEND")
    else:
        os.environ["EMBEDDING_BACKEND"] = prev

    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    req_pkgs = [ln.strip() for ln in req.splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    check("deploy requirements exclude sentence-transformers (torch)",
          not any("sentence-transformers" in ln for ln in req_pkgs))
    check("deploy requirements include pysqlite3-binary",
          any("pysqlite3-binary" in ln for ln in req_pkgs))
    check("pysqlite3-binary is linux-gated (Windows-safe)",
          any("pysqlite3-binary" in ln and 'sys_platform == "linux"' in ln
              for ln in req_pkgs))
    loc = [ln.strip() for ln in (ROOT / "requirements-local.txt").read_text(encoding="utf-8").splitlines()
           if ln.strip() and not ln.strip().startswith("#")]
    check("requirements-local.txt adds sentence-transformers",
          any("sentence-transformers" in ln for ln in loc))
    check("requirements-local.txt includes the deploy set",
          any(ln.startswith("-r requirements.txt") for ln in loc))
    check("secrets template exists and is not a real secrets file",
          (ROOT / ".streamlit/secrets.toml.example").exists()
          and not (ROOT / ".streamlit/secrets.toml").exists())
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    check(".gitignore protects .env and secrets.toml",
          ".env" in gi and "secrets.toml" in gi)
    check("deploy index builder script present",
          (ROOT / "scripts/build_index_for_deploy.py").exists())

    # Windows defaults to cp1252, so every text read/write must name utf-8 or
    # the emoji in the Streamlit pages crash the app on a Windows console.
    def _calls_without_encoding(body: str):
        """Real .read_text()/.write_text() calls lacking encoding=, found via the
        AST so string literals and docstrings can never false-positive."""
        import ast as _ast
        bad = []
        for node in _ast.walk(_ast.parse(body)):
            if (isinstance(node, _ast.Call)
                    and isinstance(node.func, _ast.Attribute)
                    and node.func.attr in ("read_text", "write_text")
                    and not any(k.arg == "encoding" for k in node.keywords)):
                bad.append(node.lineno)
        return bad

    offenders = []
    for py in ROOT.rglob("*.py"):
        if "__pycache__" in py.parts or ".venv" in py.parts:
            continue
        for line_no in _calls_without_encoding(py.read_text(encoding="utf-8")):
            offenders.append(f"{py.relative_to(ROOT)}:{line_no}")
    check("every read_text/write_text names an encoding (Windows-safe)",
          not offenders, ", ".join(offenders[:4]))

    auth_src = (ROOT / "app/_auth.py").read_text(encoding="utf-8")
    check("auth gate is inert when APP_PASSWORD is unset (documented default)",
          "if not expected:" in auth_src and "return True" in auth_src)
    check("auth gate compares in constant time", "hmac.compare_digest" in auth_src)
    check("auth gate reads APP_PASSWORD from the environment",
          'os.getenv("APP_PASSWORD")' in auth_src)
    home_src = (ROOT / "app/Home.py").read_text(encoding="utf-8")
    check("Home page reports whether the gate is on or off",
          "password gate ON" in home_src and "password gate OFF" in home_src)

    import logging as _log
    check("chroma telemetry logger is muted",
          _log.getLogger("chromadb.telemetry.product.posthog").level >= _log.CRITICAL)
    check("ANONYMIZED_TELEMETRY is set", os.getenv("ANONYMIZED_TELEMETRY") == "False")
    for page in ("app/Home.py", "app/pages/1_Data_Ingestion.py", "app/pages/2_Chat_Bot.py"):
        src = (ROOT / page).read_text(encoding="utf-8")
        check(f"{page} imports cloud_bootstrap before config",
              src.index("import cloud_bootstrap") < src.index("from config import"))
        check(f"{page} is password-gated", "require_password()" in src)

    # ---------------------------------------------------------- summary
    print(f"\n{'='*60}\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:")
        for f in FAIL:
            print("  -", f)
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
