"""Offline stand-in for sentence-transformers (tests only).

Deterministic hashed bag-of-words embedding: no download, no torch, but real
lexical-overlap similarity, which is enough to verify that retrieval ranking,
filtering and citation plumbing all work.
"""
from __future__ import annotations

import re
import zlib

import numpy as np

DIM = 384
_WORD = re.compile(r"[a-z]{3,}")
_STOP = {"the", "and", "that", "for", "with", "shall", "any", "not", "this",
         "which", "from", "under", "was", "are", "have", "has", "been"}


class SentenceTransformer:
    def __init__(self, name: str = "stub", *a, **k):
        self.name = name

    def encode(self, texts, batch_size=32, show_progress_bar=False,
               convert_to_numpy=True, normalize_embeddings=True):
        out = np.zeros((len(texts), DIM), dtype="float32")
        for i, t in enumerate(texts):
            for w in _WORD.findall(t.lower()):
                if w in _STOP:
                    continue
                out[i, zlib.crc32(w.encode()) % DIM] += 1.0
        if normalize_embeddings:
            n = np.linalg.norm(out, axis=1, keepdims=True)
            out = out / np.where(n == 0, 1, n)
        return out
