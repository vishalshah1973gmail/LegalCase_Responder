# ⚖️ LegalCase Responder

A locally-runnable **RAG chatbot for property-law case documents**. Look up riders,
paragraphs and clauses across a 120-case corpus, get an answer grounded strictly in the
retrieved text, verify the grounding side-by-side, and export the result as a
legal-memo `.docx`.

> **Research / demo tool — not legal advice.** The shipped corpus is **entirely
> synthetic**: the cases, parties, courts and docket numbers are fictional. See
> [Data sourcing](#data-sourcing-and-the-real-data-fallback).

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Streamlit, multipage (2 GUIs) |
| Vector store | ChromaDB, **persistent** client at `db/chroma/` |
| Metadata store | SQLite at `db/metadata.sqlite` (case-level + chunk-level) |
| Embeddings | `sentence-transformers` / `all-MiniLM-L6-v2` — local, free, offline |
| Answer generation | Anthropic Claude API (`anthropic` SDK), key from `ANTHROPIC_API_KEY` |
| Export | `python-docx` |

Retrieval needs **no API key**. A key is required only for the answer-writing step.

---

## Quick start

```bash
# 1. from the project root
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements-local.txt

# 2. API key (only needed for answer generation)
copy .env.example .env      # Windows
# cp .env.example .env      # macOS / Linux
#   then edit .env and paste your key after ANTHROPIC_API_KEY=

# 3. the corpus is already in data/cases/ (120 JSON files).
#    to regenerate it deterministically:
python ingestion/corpus_builder.py -n 120

# 4. launch both GUIs (one app, two pages)
streamlit run app/Home.py
```

Streamlit opens at <http://localhost:8501>. The sidebar has **Data Ingestion** and
**Chat Bot**.

First ingestion downloads the ~90 MB MiniLM model once; everything after that is offline.

You can also ingest headlessly:

```bash
python ingestion/ingest.py                 # skip-if-unchanged
python ingestion/ingest.py --force         # re-embed everything
python ingestion/ingest.py --reset         # wipe both stores first
```

---

## GUI 1 — Data Ingestion

* One-click ingestion of `data/cases/*.json` with a progress bar and a live log
  (case being processed, per-case chunk counts).
* **Chunking config in the sidebar.** The default boundary is **one
  rider / paragraph / clause per chunk** — that is the retrieval granularity. Any single
  section longer than *Max characters per chunk* is split further into overlapping
  sub-chunks (*Overlap* slider), and those parts are labelled `(pt. 2)` in citations so
  a split is always visible.
* **Summary stats** after ingestion: total cases, total chunks, breakdown by source
  (real vs synthetic), by case type, by section type and by jurisdiction.
* **Safe re-ingest.** Each case is hashed over its section content. An unchanged case is
  *skipped*; a changed case is *upserted* — its old vectors are deleted from Chroma and
  its old rows from SQLite before the new ones are written. Re-running never duplicates.
* A reset button clears both stores for a clean rebuild.

## GUI 2 — Chat Bot

* Natural-language question box, e.g. *"What does the rider on late fees typically say in
  landlord-tenant cases?"* or *"Find paragraphs about adverse possession boundary
  disputes"*.
* **Pre-search filters**: case, jurisdiction, case type, section type, source.
* **Top-k retrieved chunks shown next to the answer** — case name, section type and
  number, source tag (🟢 REAL / 🟠 SYNTHETIC), court, date, similarity score and
  `chunk_id` — so every claim can be checked against its excerpt.
* A **minimum-similarity floor** discards weak matches *before* generation, so a
  loosely-related chunk cannot be used to ground an answer.
* **Grounded generation.** The system prompt restricts Claude to the retrieved excerpts,
  requires a `(Case Name, Rider 2)` / `(Case Name, para. 7)` citation on every
  substantive claim, and requires it to say plainly when the excerpts do not answer the
  question rather than inventing one. With zero retrieved chunks the app does not call
  the API at all — it returns a "nothing matched" message.
* **Permanent disclaimer** on every page, in the sidebar, and inside every export.
* **Download as .docx** — a legal-memo document: heading block, *Question Presented*,
  *Answer*, and a *Sources* section listing each cited excerpt verbatim with its case
  name, section number, court, date, source tag and similarity.

---

## Data sourcing and the "real data" fallback

The spec asks for real, freely-available case text first, with synthetic generation
covering any shortfall.

**What happened:** this project was built in a sandbox whose network egress allows only
package registries. Every free legal source was refused at the proxy —
`courtlistener.com`, `api.case.law` / `static.case.law`, and `law.justia.com` all
returned `403 Tunnel connection failed` (and CourtListener additionally disallows
automated fetching via `robots.txt` for the fetch tool used). No paywalled or
ToS-restricted source was attempted.

**The documented fallback was therefore taken: the shipped corpus is 100 % synthetic —
120 cases, `source: "synthetic"`.** The pipeline is fully source-agnostic, and every
case, chunk, UI row and export carries its `source` tag, so a mixed corpus is traceable
end to end.

### Adding real cases yourself

`ingestion/fetch_real.py` is written and ready. From a machine with normal internet
access:

```bash
python ingestion/fetch_real.py --per-query 5     # ~50 real opinions
python ingestion/ingest.py                       # index them (existing cases are skipped)
```

It queries the **free, public CourtListener REST API** (public-domain U.S. opinions),
splits each opinion into numbered paragraphs, tags it `source: "real"`, and records the
CourtListener URL for attribution. `COURTLISTENER_TOKEN` in `.env` is optional and only
raises the rate limit. If a query fails, the script logs and continues rather than
aborting.

### How the synthetic cases are kept clearly fictional

* Jurisdictions are **invented states** (Westmarch, Calloway, Northridge, …) — no real
  court is imitated.
* Docket numbers use a reserved `SYN-` prefix that cannot collide with a real docket.
* Party, firm and place names come from invented pools.
* Every record carries `source: "synthetic"` plus an explicit `fictional_notice` field.
* Generation is deterministic (`--seed`), so the corpus rebuilds byte-for-byte.

Cases span 10 property-law areas — landlord-tenant, easements, boundary/title,
HOA/covenant, foreclosure, adverse possession, zoning, lease riders & addenda, eminent
domain, and water/mineral rights — 12 each. Each case has 8–12 numbered paragraphs,
1–3 riders/addenda and 2–4 clauses: **1,800+ retrievable sections**.

---

## Project layout

```
LegalCase_Responder/
├── app/
│   ├── Home.py                     # Streamlit entry point + index status
│   └── pages/
│       ├── 1_Data_Ingestion.py     # GUI 1
│       └── 2_Chat_Bot.py           # GUI 2
├── ingestion/
│   ├── corpus_builder.py           # synthetic corpus generator (deterministic)
│   ├── fetch_real.py               # optional CourtListener fetcher (real cases)
│   ├── chunker.py                  # section-aware chunking + overlap splitting
│   └── ingest.py                   # chunk → embed → Chroma + SQLite (skip/upsert)
├── retrieval/
│   ├── embedder.py                 # local sentence-transformers embeddings
│   ├── store.py                    # SQLite schema + persistent Chroma client
│   ├── search.py                   # filtered top-k semantic search
│   ├── generate.py                 # grounded Claude prompt + call
│   └── export_docx.py              # legal-memo .docx builder
├── data/cases/                     # 120 case JSON files (raw corpus, re-ingestable)
├── db/                             # chroma/ + metadata.sqlite (created on first run)
├── tests/
│   ├── smoke_test.py               # 50-check end-to-end test
│   └── stubs/                      # offline stand-ins for chroma / embeddings
├── scripts/
│   └── build_index_for_deploy.py   # prebuild the committed index (ONNX backend)
├── cloud_bootstrap.py              # sqlite3 shim + Streamlit secrets bridge
├── config.py
├── requirements.txt                # cloud/deploy set (no PyTorch)
├── requirements-local.txt          # local set (adds sentence-transformers)
├── .streamlit/secrets.toml.example
├── DEPLOYMENT.md
├── .env.example
└── README.md
```

### Case JSON shape

```jsonc
{
  "case_id": "SYN-LANDLO-0000",
  "case_name": "Havershaw v. Stonebrook Realty Trust",
  "full_caption": "...",
  "court": "Court of Appeals of Westmarch",
  "jurisdiction": "Westmarch",
  "date": "2013-04-18",
  "case_type": "landlord_tenant",
  "source": "synthetic",
  "docket_number": "SYN-2013-4471",
  "sections": [
    { "section_type": "paragraph", "section_number": "1", "heading": "Paragraph 1",
      "order": 1, "text": "..." },
    { "section_type": "rider", "section_number": "RIDER A",
      "heading": "RIDER A — LATE CHARGES AND RETURNED PAYMENTS", "order": 13, "text": "..." },
    { "section_type": "clause", "section_number": "1",
      "heading": "Clause 1 — Governing Law", "order": 15, "text": "..." }
  ]
}
```

Drop any JSON of this shape into `data/cases/` (a single object or a list) and re-ingest.

### Metadata stored in SQLite

`cases` — `case_id, case_name, full_caption, court, jurisdiction, date, case_type,
source, docket_number, property_address, source_url, n_sections, content_hash,
ingested_at`

`chunks` — `chroma_chunk_id, case_id, case_name, court, jurisdiction, date, case_type,
source, section_type, section_number, heading, ord, part, n_parts, n_chars, text`

`chroma_chunk_id` is the join key to the Chroma vector of the same id.

---

## Deploying to Streamlit Community Cloud

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the full step-by-step. The short version:

```bash
pip install -r requirements-local.txt
python scripts/build_index_for_deploy.py     # prebuild the index (~6 MB)
git add . && git add -f db/ && git commit -m "deploy" && git push
```

Then at <https://share.streamlit.io>: **Create app** → your repo → branch `main` →
main file path **`app/Home.py`** → Advanced settings: Python **3.11** and paste the
secrets from `.streamlit/secrets.toml.example`.

Three constraints are already handled for you:

* **2.7 GB RAM ceiling.** `requirements.txt` (the file Community Cloud installs) omits
  `sentence-transformers`, because it pulls ~1 GB of PyTorch. On the cloud the app
  embeds with ChromaDB's bundled **ONNX** build of the same `all-MiniLM-L6-v2` model.
  `requirements-local.txt` adds PyTorch back for local work, and
  `EMBEDDING_BACKEND=auto` picks whichever is installed.
* **Old system sqlite3.** ChromaDB needs ≥ 3.35; Community Cloud ships older.
  `pysqlite3-binary` plus the swap in `cloud_bootstrap.py` fixes it transparently.
* **Ephemeral filesystem.** The index is prebuilt and committed, and the deployed app
  runs with `READ_ONLY = "true"` so the ingestion controls are disabled.

Set `APP_PASSWORD` in secrets to gate the public URL — answer generation bills your
Anthropic key on every question.

---

## Tests

```bash
python tests/smoke_test.py
```

79 checks across corpus integrity, chunking (including overlap splitting), ingestion
(skip / upsert / no-duplicates), filtered retrieval, prompt construction, docx structure,
the SQLite ↔ Chroma consistency invariant, and deployment readiness (sqlite shim, backend selection, requirements split, secrets hygiene). It runs against the **real** drivers when
they are installed and falls back to the offline stubs in `tests/stubs/` when they are
not, so it works air-gapped. It uses a scratch database and never touches `db/`.

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Required for answer generation only |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Generation model |
| `ANTHROPIC_MAX_TOKENS` | `1500` | Answer length cap |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Any sentence-transformers model |
| `EMBEDDING_BACKEND` | `auto` | `auto` \| `sentence-transformers` \| `onnx` |
| `APP_PASSWORD` | *(empty)* | Shared password gate; empty means open |
| `READ_ONLY` | *(empty)* | `true` disables ingestion (ephemeral hosts) |
| `COURTLISTENER_TOKEN` | *(empty)* | Optional, raises the real-data fetch rate limit |

The key is read from the environment and is never hard-coded. `.env` is git-ignored.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` in the Chat Bot | Create `.env` from `.env.example`, add the key, restart Streamlit. Retrieval still works without it. |
| First ingestion hangs a minute | It is downloading the MiniLM weights once. Later runs are offline. |
| "The index is empty" on the Chat Bot | Run **Data Ingestion** first. |
| Nothing retrieved | Lower *Minimum similarity* or clear the filters — a filter combination can legitimately match nothing. |
| Duplicate-looking results after edits | Use **Reset both stores**, then ingest. |
| `sqlite3.OperationalError: database is locked` | Two Streamlit processes are open on the same `db/`. Close one. |
