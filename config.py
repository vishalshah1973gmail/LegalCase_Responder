"""Central configuration for LegalCase Responder.

All paths are absolute and derived from this file's location, so the app can be
launched from any working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is in requirements.txt, but stay import-safe
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------- paths
DATA_DIR = PROJECT_ROOT / "data"
CASES_DIR = DATA_DIR / "cases"
DB_DIR = PROJECT_ROOT / "db"
CHROMA_DIR = DB_DIR / "chroma"
SQLITE_PATH = DB_DIR / "metadata.sqlite"

for _p in (DATA_DIR, CASES_DIR, DB_DIR, CHROMA_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- vector store
CHROMA_COLLECTION = "legalcase_sections"

# ---------------------------------------------------------------- embeddings
# Local, free, offline-capable sentence-transformers model.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ---------------------------------------------------------------- chunking
# Default boundary is ONE rider / paragraph / clause per chunk. A single section
# longer than MAX_CHUNK_CHARS is split further, with CHUNK_OVERLAP_CHARS overlap.
DEFAULT_MAX_CHUNK_CHARS = 1800
DEFAULT_CHUNK_OVERLAP_CHARS = 200

# ---------------------------------------------------------------- generation
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
ANTHROPIC_MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1500"))

DEFAULT_TOP_K = 8

DISCLAIMER = (
    "**Research / demo tool — not legal advice.** This corpus is partly (in the "
    "shipped build, entirely) **synthetic**: the cases, parties, courts and docket "
    "numbers are fictional and were generated for demonstration. Nothing here states "
    "the law of any jurisdiction. Do not rely on it for any legal decision. Consult a "
    "licensed attorney."
)

SECTION_TYPES = ["rider", "paragraph", "clause"]
SOURCES = ["real", "synthetic"]
