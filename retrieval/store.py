"""Persistence layer: SQLite for metadata, ChromaDB (persistent) for vectors."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import CHROMA_COLLECTION, CHROMA_DIR, SQLITE_PATH  # noqa: E402


def _silence_chroma_telemetry() -> None:
    """Suppress ChromaDB's anonymous product telemetry and its error spam.

    Some chromadb releases call PostHog's ``capture()`` with a signature newer
    PostHog versions rejected, producing a line of
    ``Failed to send telemetry event ...: capture() takes 1 positional argument
    but 3 were given`` for every single operation. It is entirely cosmetic — no
    data leaves the machine either way — but it drowns real output.

    ``anonymized_telemetry=False`` alone does not stop it (the telemetry client
    still initializes), so we also mute the logger. Both are version-proof.
    """
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    for name in ("chromadb.telemetry", "chromadb.telemetry.product",
                 "chromadb.telemetry.product.posthog", "posthog"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.CRITICAL)
        lg.propagate = False


_silence_chroma_telemetry()

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id        TEXT PRIMARY KEY,
    case_name      TEXT NOT NULL,
    full_caption   TEXT,
    court          TEXT,
    jurisdiction   TEXT,
    date           TEXT,
    case_type      TEXT,
    source         TEXT CHECK (source IN ('real','synthetic')),
    docket_number  TEXT,
    property_address TEXT,
    source_url     TEXT,
    n_sections     INTEGER DEFAULT 0,
    content_hash   TEXT,
    ingested_at    TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chroma_chunk_id TEXT PRIMARY KEY,
    case_id        TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    case_name      TEXT,
    court          TEXT,
    jurisdiction   TEXT,
    date           TEXT,
    case_type      TEXT,
    source         TEXT,
    section_type   TEXT CHECK (section_type IN ('rider','paragraph','clause')),
    section_number TEXT,
    heading        TEXT,
    ord            INTEGER,
    part           INTEGER,
    n_parts        INTEGER,
    n_chars        INTEGER,
    text           TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_case      ON chunks(case_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type      ON chunks(case_type);
CREATE INDEX IF NOT EXISTS idx_chunks_sectype   ON chunks(section_type);
CREATE INDEX IF NOT EXISTS idx_chunks_source    ON chunks(source);
CREATE INDEX IF NOT EXISTS idx_cases_juris      ON cases(jurisdiction);
"""


# ------------------------------------------------------------------ SQLite
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def case_hash(case: Dict[str, Any]) -> str:
    import hashlib
    payload = json.dumps(case.get("sections", []), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def ingested_hash(conn: sqlite3.Connection, case_id: str) -> Optional[str]:
    row = conn.execute("SELECT content_hash FROM cases WHERE case_id = ?",
                       (case_id,)).fetchone()
    return row["content_hash"] if row else None


def upsert_case(conn: sqlite3.Connection, case: Dict[str, Any], chash: str) -> None:
    from datetime import datetime, timezone
    conn.execute(
        """INSERT INTO cases (case_id, case_name, full_caption, court, jurisdiction,
                              date, case_type, source, docket_number, property_address,
                              source_url, n_sections, content_hash, ingested_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(case_id) DO UPDATE SET
             case_name=excluded.case_name, full_caption=excluded.full_caption,
             court=excluded.court, jurisdiction=excluded.jurisdiction,
             date=excluded.date, case_type=excluded.case_type,
             source=excluded.source, docket_number=excluded.docket_number,
             property_address=excluded.property_address,
             source_url=excluded.source_url, n_sections=excluded.n_sections,
             content_hash=excluded.content_hash, ingested_at=excluded.ingested_at""",
        (case["case_id"], case["case_name"], case.get("full_caption", ""),
         case.get("court", ""), case.get("jurisdiction", ""), case.get("date", ""),
         case.get("case_type", ""), case.get("source", "synthetic"),
         case.get("docket_number", ""), case.get("property_address", ""),
         case.get("source_url", ""), len(case.get("sections", [])), chash,
         datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )


def replace_chunks(conn: sqlite3.Connection, case_id: str,
                   chunks: Sequence[Any]) -> None:
    conn.execute("DELETE FROM chunks WHERE case_id = ?", (case_id,))
    conn.executemany(
        """INSERT INTO chunks (chroma_chunk_id, case_id, case_name, court, jurisdiction,
                               date, case_type, source, section_type, section_number,
                               heading, ord, part, n_parts, n_chars, text)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(c.chunk_id, c.case_id, c.case_name, c.court, c.jurisdiction, c.date,
          c.case_type, c.source, c.section_type, c.section_number, c.heading,
          c.order, c.part, c.n_parts, len(c.text), c.text) for c in chunks],
    )


def stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    q = lambda s, *a: conn.execute(s, a).fetchall()  # noqa: E731
    return {
        "total_cases": q("SELECT COUNT(*) c FROM cases")[0]["c"],
        "total_chunks": q("SELECT COUNT(*) c FROM chunks")[0]["c"],
        "by_source": {r["source"]: r["c"] for r in
                      q("SELECT source, COUNT(*) c FROM cases GROUP BY source")},
        "chunks_by_source": {r["source"]: r["c"] for r in
                             q("SELECT source, COUNT(*) c FROM chunks GROUP BY source")},
        "by_case_type": {r["case_type"]: r["c"] for r in
                         q("SELECT case_type, COUNT(*) c FROM cases "
                           "GROUP BY case_type ORDER BY c DESC")},
        "chunks_by_section_type": {r["section_type"]: r["c"] for r in
                                   q("SELECT section_type, COUNT(*) c FROM chunks "
                                     "GROUP BY section_type ORDER BY c DESC")},
        "by_jurisdiction": {r["jurisdiction"]: r["c"] for r in
                            q("SELECT jurisdiction, COUNT(*) c FROM cases "
                              "GROUP BY jurisdiction ORDER BY c DESC")},
    }


def distinct(conn: sqlite3.Connection, column: str) -> List[str]:
    allowed = {"case_name", "jurisdiction", "case_type", "source", "court"}
    if column not in allowed:
        raise ValueError(f"column must be one of {allowed}")
    rows = conn.execute(
        f"SELECT DISTINCT {column} v FROM cases WHERE {column} <> '' ORDER BY v")
    return [r["v"] for r in rows]


def chunks_for_case(conn: sqlite3.Connection, case_id: str) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM chunks WHERE case_id = ? ORDER BY ord, part", (case_id,)).fetchall()


# ------------------------------------------------------------------ Chroma
_client = None


def chroma_client():
    """Persistent Chroma client rooted at ``db/chroma`` (never in-memory)."""
    global _client
    if _client is None:
        import chromadb
        from chromadb.config import Settings
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
    return _client


def collection():
    return chroma_client().get_or_create_collection(
        name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})


def reset_all() -> None:
    """Drop the vector collection and the metadata tables (full re-ingest)."""
    try:
        chroma_client().delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    conn = connect()
    conn.executescript("DELETE FROM chunks; DELETE FROM cases;")
    conn.commit()
    conn.close()
