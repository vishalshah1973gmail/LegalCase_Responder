"""Local embeddings — free, offline, no paid API.

Two interchangeable backends, both running the SAME model
(`all-MiniLM-L6-v2`, 384 dims), so vectors from either are compatible:

* ``sentence-transformers`` (PyTorch). The default on a local machine.
* ``onnx`` — ChromaDB's bundled ONNX build of all-MiniLM-L6-v2. No PyTorch,
  roughly 150 MB instead of ~1 GB, which is what makes the app fit inside
  Streamlit Community Cloud's 2.7 GB memory ceiling.

Selection order:
  1. ``EMBEDDING_BACKEND`` env var — ``sentence-transformers`` | ``onnx`` | ``auto``
  2. ``auto`` (the default): sentence-transformers if importable, else onnx.

Both paths return L2-normalized vectors, so cosine similarity is a dot product.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EMBEDDING_MODEL  # noqa: E402

_model = None
_backend: str | None = None


def _choose_backend() -> str:
    want = os.getenv("EMBEDDING_BACKEND", "auto").strip().lower()
    if want in ("st", "sentence-transformers", "sentence_transformers"):
        return "sentence-transformers"
    if want == "onnx":
        return "onnx"
    if importlib.util.find_spec("sentence_transformers") is not None:
        return "sentence-transformers"
    return "onnx"


class _OnnxEmbedder:
    """Adapter giving ChromaDB's ONNX MiniLM the same .encode() surface."""

    def __init__(self) -> None:
        from chromadb.utils import embedding_functions
        self._fn = embedding_functions.ONNXMiniLM_L6_V2()

    def encode(self, texts, batch_size=32, show_progress_bar=False,
               convert_to_numpy=True, normalize_embeddings=True):
        import numpy as np
        out = np.asarray(self._fn(list(texts)), dtype="float32")
        if normalize_embeddings:
            n = np.linalg.norm(out, axis=1, keepdims=True)
            out = out / np.where(n == 0, 1, n)
        return out


def backend() -> str:
    """Which backend is in use (loads the model on first call)."""
    get_model()
    return _backend or "unknown"


def get_model():
    global _model, _backend
    if _model is None:
        _backend = _choose_backend()
        if _backend == "onnx":
            _model = _OnnxEmbedder()
        else:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed(texts: Sequence[str], batch_size: int = 32,
          show_progress: bool = False) -> List[List[float]]:
    vecs = get_model().encode(
        list(texts), batch_size=batch_size, show_progress_bar=show_progress,
        convert_to_numpy=True, normalize_embeddings=True)
    return [v.tolist() for v in vecs]


def embed_one(text: str) -> List[float]:
    return embed([text])[0]
