"""Build the index that ships with the deployed app.

Streamlit Community Cloud gives every app an EPHEMERAL filesystem: anything
written at runtime is gone on the next reboot. So the vector store and the
metadata database are built once here, on your machine, and committed to the
repository.

It forces the ONNX backend so the committed vectors are produced by exactly the
same code path the deployed app queries with.

    python scripts/build_index_for_deploy.py

Then commit the result:

    git add -f db/
    git commit -m "Prebuilt index for deployment"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["EMBEDDING_BACKEND"] = "onnx"   # must be set before embedder loads

import cloud_bootstrap  # noqa: E402,F401
from config import CHROMA_DIR, SQLITE_PATH  # noqa: E402
from ingestion.ingest import ingest  # noqa: E402
from retrieval import embedder, store  # noqa: E402


def _size(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / 1e6
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def main() -> int:
    print(f"sqlite3: {cloud_bootstrap.SQLITE_STATUS}")
    print("Resetting stores for a clean, reproducible build …")
    store.reset_all()

    summary = ingest(force=True)
    print(f"\nembedding backend used: {embedder.backend()}")
    if embedder.backend() != "onnx":
        print("WARNING: expected the onnx backend. Vectors may not match the "
              "deployed app's query embeddings.")

    print(f"\ncases:  {summary['total_cases']}")
    print(f"chunks: {summary['total_chunks']}")
    print(f"by source: {summary['by_source']}")
    print(f"\ndb/chroma        {_size(CHROMA_DIR):8.1f} MB")
    print(f"db/metadata.sqlite {_size(SQLITE_PATH):6.1f} MB")
    total = _size(CHROMA_DIR) + _size(SQLITE_PATH)
    print(f"total to commit  {total:8.1f} MB")
    if total > 90:
        print("\nWARNING: over ~90 MB. GitHub warns above 50 MB per file and "
              "rejects above 100 MB. Consider fewer cases or Git LFS.")

    print("\nNext:\n  git add -f db/\n  git commit -m \"Prebuilt index for deployment\"\n  git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
