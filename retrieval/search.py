"""Filtered semantic retrieval over the persisted Chroma collection."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEFAULT_TOP_K  # noqa: E402
from retrieval import embedder, store  # noqa: E402


@dataclass
class Hit:
    chunk_id: str
    text: str
    score: float          # cosine similarity, 1.0 == identical
    meta: Dict[str, Any]

    @property
    def case_name(self) -> str:
        return self.meta.get("case_name", "Unknown case")

    @property
    def section_type(self) -> str:
        return self.meta.get("section_type", "")

    @property
    def section_number(self) -> str:
        return str(self.meta.get("section_number", ""))

    @property
    def source(self) -> str:
        return self.meta.get("source", "")

    def citation(self) -> str:
        label = {"rider": "Rider", "paragraph": "para.",
                 "clause": "Clause"}.get(self.section_type, self.section_type)
        num = str(self.section_number).strip()
        # section_number may already carry its own label (e.g. "RIDER 1")
        if num.lower().startswith(label.rstrip(".").lower()):
            cite = f"{self.case_name}, {num.title() if num.isupper() else num}"
        else:
            cite = f"{self.case_name}, {label} {num}"
        if int(self.meta.get("n_parts", 1)) > 1:
            cite += f" (pt. {int(self.meta.get('part', 0)) + 1})"
        return cite


def _where(case_names: Optional[List[str]] = None,
           jurisdictions: Optional[List[str]] = None,
           case_types: Optional[List[str]] = None,
           section_types: Optional[List[str]] = None,
           sources: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Build a Chroma ``where`` filter from the UI selections."""
    clauses: List[Dict[str, Any]] = []
    for field, values in (("case_name", case_names), ("jurisdiction", jurisdictions),
                          ("case_type", case_types), ("section_type", section_types),
                          ("source", sources)):
        if values:
            clauses.append({field: {"$in": list(values)}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def search(query: str, top_k: int = DEFAULT_TOP_K,
           min_score: float = 0.0, **filters) -> List[Hit]:
    """Embed the query and return the top-k most similar chunks."""
    if not query.strip():
        return []
    col = store.collection()
    if col.count() == 0:
        return []
    res = col.query(
        query_embeddings=[embedder.embed_one(query)],
        n_results=min(top_k, col.count()),
        where=_where(**filters),
        include=["documents", "metadatas", "distances"],
    )
    hits: List[Hit] = []
    ids = res.get("ids", [[]])[0]
    for i, cid in enumerate(ids):
        dist = res["distances"][0][i]
        score = 1.0 - float(dist)          # cosine space
        if score < min_score:
            continue
        hits.append(Hit(chunk_id=cid, text=res["documents"][0][i],
                        score=score, meta=res["metadatas"][0][i]))
    return hits


def filter_options() -> Dict[str, List[str]]:
    conn = store.connect()
    try:
        return {
            "case_name": store.distinct(conn, "case_name"),
            "jurisdiction": store.distinct(conn, "jurisdiction"),
            "case_type": store.distinct(conn, "case_type"),
            "source": store.distinct(conn, "source"),
        }
    finally:
        conn.close()
