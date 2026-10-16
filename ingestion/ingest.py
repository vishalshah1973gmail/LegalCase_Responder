"""Ingestion pipeline: load /data corpus -> chunk -> embed -> Chroma + SQLite.

Re-ingestion is safe. Each case is hashed by the content of its sections; a case
whose hash matches what SQLite already records is SKIPPED, and a case whose hash
changed is UPSERTED (its old chunks are deleted from both stores first), so no
duplicates are ever created.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import CASES_DIR, DEFAULT_CHUNK_OVERLAP_CHARS, DEFAULT_MAX_CHUNK_CHARS  # noqa: E402
from ingestion.chunker import Chunk, chunk_case  # noqa: E402
from retrieval import embedder, store  # noqa: E402

Logger = Callable[[str], None]


def load_corpus(cases_dir: Path | None = None) -> List[Dict[str, Any]]:
    d = Path(cases_dir) if cases_dir else CASES_DIR
    cases: List[Dict[str, Any]] = []
    for p in sorted(d.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        # a file may hold one case or a list of cases
        for c in (data if isinstance(data, list) else [data]):
            if c.get("case_id") and c.get("sections"):
                cases.append(c)
    return cases


def _chunk_metadata(c: Chunk) -> Dict[str, Any]:
    """Chroma metadata must be flat scalars."""
    return {
        "case_id": c.case_id, "case_name": c.case_name, "court": c.court,
        "jurisdiction": c.jurisdiction, "date": c.date, "case_type": c.case_type,
        "source": c.source, "section_type": c.section_type,
        "section_number": c.section_number, "heading": c.heading,
        "order": c.order, "part": c.part, "n_parts": c.n_parts,
    }


def ingest(
    cases: Optional[List[Dict[str, Any]]] = None,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    log: Logger = print,
    progress: Optional[Callable[[float, str], None]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Ingest the corpus. Returns a summary dict."""
    cases = cases if cases is not None else load_corpus()
    total = len(cases)
    log(f"Loaded {total} cases from {CASES_DIR}")
    if total == 0:
        log("No cases found. Generate the corpus first (see README).")
        return {"cases_ingested": 0, "cases_skipped": 0, "chunks_written": 0}

    conn = store.connect()
    col = store.collection()
    log(f"Embedding model: loading (first run downloads ~90 MB) ...")
    embedder.get_model()
    log("Embedding model ready.")

    n_new = n_skip = n_chunks = 0
    for i, case in enumerate(cases, start=1):
        cid = case["case_id"]
        chash = store.case_hash(case)
        if not force and store.ingested_hash(conn, cid) == chash:
            n_skip += 1
            if progress:
                progress(i / total, f"skip {cid} (already ingested)")
            continue

        chunks = chunk_case(case, max_chars=max_chars, overlap=overlap)
        # remove any previous vectors for this case before re-adding (upsert)
        try:
            col.delete(where={"case_id": cid})
        except Exception:
            pass

        vectors = embedder.embed([c.text for c in chunks])
        col.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[_chunk_metadata(c) for c in chunks],
        )
        store.upsert_case(conn, case, chash)
        store.replace_chunks(conn, cid, chunks)
        conn.commit()

        n_new += 1
        n_chunks += len(chunks)
        msg = (f"[{i}/{total}] {cid}  {case['case_name']}  "
               f"({case.get('source')}, {len(chunks)} chunks)")
        log(msg)
        if progress:
            progress(i / total, msg)

    summary = store.stats(conn)
    summary.update({"cases_ingested": n_new, "cases_skipped": n_skip,
                    "chunks_written": n_chunks})
    conn.close()
    log(f"Done. {n_new} ingested, {n_skip} skipped, {n_chunks} chunks written.")
    return summary


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Ingest the /data corpus.")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHUNK_CHARS)
    ap.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP_CHARS)
    ap.add_argument("--force", action="store_true", help="re-embed every case")
    ap.add_argument("--reset", action="store_true", help="wipe both stores first")
    a = ap.parse_args()
    if a.reset:
        store.reset_all()
        print("Stores reset.")
    s = ingest(max_chars=a.max_chars, overlap=a.overlap, force=a.force)
    print(json.dumps({k: v for k, v in s.items()}, indent=2))
