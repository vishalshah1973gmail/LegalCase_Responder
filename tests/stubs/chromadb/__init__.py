"""Minimal offline stand-in for chromadb, used ONLY by tests/smoke_test.py.

It implements the exact surface this project uses (PersistentClient,
get_or_create_collection, upsert, delete(where), count, query) with cosine
similarity over the supplied vectors, and persists to a JSON file so the
persistence semantics of the real PersistentClient are exercised too.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


def _match(meta: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
    if not where:
        return True
    if "$and" in where:
        return all(_match(meta, w) for w in where["$and"])
    if "$or" in where:
        return any(_match(meta, w) for w in where["$or"])
    for field, cond in where.items():
        val = meta.get(field)
        if isinstance(cond, dict):
            if "$in" in cond and val not in cond["$in"]:
                return False
            if "$eq" in cond and val != cond["$eq"]:
                return False
            if "$ne" in cond and val == cond["$ne"]:
                return False
        elif val != cond:
            return False
    return True


def _cos(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return num / (na * nb)


class Collection:
    def __init__(self, name: str, path: Path, metadata=None):
        self.name = name
        self._file = path / f"{name}.json"
        self.metadata = metadata or {}
        self._rows: Dict[str, Dict[str, Any]] = {}
        if self._file.exists():
            self._rows = json.loads(self._file.read_text(encoding="utf-8"))

    def _flush(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._rows), encoding="utf-8")

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, _id in enumerate(ids):
            self._rows[_id] = {"e": list(embeddings[i]), "d": documents[i],
                               "m": dict(metadatas[i])}
        self._flush()

    add = upsert

    def delete(self, ids=None, where=None):
        if ids:
            for i in ids:
                self._rows.pop(i, None)
        if where is not None:
            for k in [k for k, v in self._rows.items() if _match(v["m"], where)]:
                del self._rows[k]
        self._flush()

    def count(self) -> int:
        return len(self._rows)

    def query(self, query_embeddings, n_results=10, where=None, include=None):
        q = query_embeddings[0]
        scored = [(1.0 - _cos(q, r["e"]), k, r) for k, r in self._rows.items()
                  if _match(r["m"], where)]
        scored.sort(key=lambda t: t[0])
        top = scored[:n_results]
        return {
            "ids": [[k for _, k, _ in top]],
            "documents": [[r["d"] for _, _, r in top]],
            "metadatas": [[r["m"] for _, _, r in top]],
            "distances": [[d for d, _, _ in top]],
        }


class PersistentClient:
    def __init__(self, path: str, settings=None):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._cols: Dict[str, Collection] = {}

    def get_or_create_collection(self, name: str, metadata=None) -> Collection:
        if name not in self._cols:
            self._cols[name] = Collection(name, self.path, metadata)
        return self._cols[name]

    def delete_collection(self, name: str) -> None:
        f = self.path / f"{name}.json"
        if f.exists():
            f.unlink()
        self._cols.pop(name, None)
