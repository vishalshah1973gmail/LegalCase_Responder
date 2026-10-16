# Deploying LegalCase Responder to Streamlit Community Cloud

Step-by-step, start to finish. Budget ~30 minutes, most of it the first build.

Everything the app needs to run on Community Cloud is already in this repo — the
sqlite3 shim, the light embedding backend, the secrets bridge and the password gate.
You mainly need to **build the index, push to GitHub, and paste secrets**.

---

## Why this app needs the extra steps

Community Cloud is generous but constrained, and three of its properties bite this app:

| Constraint | Effect here | Handled by |
|---|---|---|
| **2.7 GB max RAM** per app | `sentence-transformers` drags in ~1 GB of PyTorch and the app gets killed | `requirements.txt` omits it; the app embeds via ChromaDB's bundled **ONNX** build of the same `all-MiniLM-L6-v2` model (~150 MB) |
| **Old system `sqlite3`** on their image | ChromaDB refuses to start: *"unsupported version of sqlite3, Chroma requires ≥ 3.35"* | `pysqlite3-binary` in `requirements.txt` + the swap in `cloud_bootstrap.py` |
| **Ephemeral filesystem** | Anything ingested at runtime vanishes on the next reboot | The index is **prebuilt and committed**; the deployed app runs in `READ_ONLY` mode |

You do not have to implement any of that. Just don't undo it.

---

## Step 0 — What you need

- A **GitHub account**.
- **Git** installed (`git --version`).
- An **Anthropic API key** — <https://console.anthropic.com> → API Keys.
- A Streamlit Community Cloud account — sign in at <https://share.streamlit.io> with GitHub.

---

## Step 1 — Install locally and confirm the app runs

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements-local.txt
python tests/smoke_test.py        # expect: 79 passed, 0 failed
streamlit run app/Home.py
```

Ingest on page 1, ask a question on page 2. **Get it working locally first** —
debugging on Community Cloud is much slower.

---

## Step 2 — Build the index that will ship with the app

The deployed app cannot build its own index, so you build it here and commit it.

```bash
python scripts/build_index_for_deploy.py
```

This wipes and rebuilds both stores with `EMBEDDING_BACKEND=onnx`, so the committed
vectors come from the exact code path the deployed app queries with. It prints the
size to commit — expect roughly:

```
db/chroma          ~3-6 MB
db/metadata.sqlite ~2-3 MB
```

Well under GitHub's 50 MB-per-file warning. If you later grow the corpus past
~10,000 chunks, re-check that number.

> **Why not just let the cloud app ingest on first run?** It would work once, then
> disappear on the next reboot, re-run on every wake-up, and spend your memory budget
> embedding 1,800 sections instead of serving queries.

---

## Step 3 — Put the project on GitHub

```bash
git init
git add .
git add -f db/                    # -f because .gitignore excludes db/ by default
git commit -m "LegalCase Responder: RAG chatbot over property-law corpus"
```

Check that no secret is staged before you push:

```bash
git status --short
git ls-files | findstr /I ".env secrets.toml"     # Windows — expect only *.example
# git ls-files | grep -Ei '\.env$|secrets\.toml$' # macOS / Linux — expect no output
```

`.env` and `.streamlit/secrets.toml` are git-ignored. Only the `.example` files
should ever appear. **If a real key ever gets committed, rotate it** — deleting the
file later does not remove it from git history.

Create the repo on GitHub (`legalcase-responder`), then:

```bash
git remote add origin https://github.com/<your-username>/legalcase-responder.git
git branch -M main
git push -u origin main
```

Public or private both work. Private repos need Streamlit's GitHub authorization,
which it prompts for on first sign-in.

---

## Step 4 — Create the app on Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository**: `<your-username>/legalcase-responder`
   - **Branch**: `main`
   - **Main file path**: `app/Home.py`   ← not `streamlit_app.py`
   - **App URL**: pick your subdomain, e.g. `legalcase-responder`
4. Open **Advanced settings**:
   - **Python version**: **3.11** (3.12 also works; avoid 3.13 — some wheels lag)
   - **Secrets**: paste the block below, with your real values.

```toml
ANTHROPIC_API_KEY = "sk-ant-your-real-key"
ANTHROPIC_MODEL   = "claude-sonnet-5"
APP_PASSWORD      = "pick-something-shareable"
READ_ONLY         = "true"
EMBEDDING_BACKEND = "onnx"
```

5. Click **Deploy**.

The first build takes 5–10 minutes — it is compiling the dependency set. Watch the
log pane on the right; it streams pip output and any traceback.

---

## Step 5 — Verify the live app

Open your URL and check, in order:

1. **Password prompt appears** → `APP_PASSWORD` was read from secrets.
2. **Home page shows** `Cases indexed: 120`, `Chunks indexed: 1822` → the committed
   index loaded. Expand **Configuration**; sqlite3 should say *"swapped in pysqlite3…"*.
3. **Data Ingestion page** shows the 🔒 read-only banner with disabled buttons.
4. **Chat Bot page** — ask *"What does the rider on late fees typically say in
   landlord-tenant cases?"* You should get retrieved chunks on the right and a cited
   answer on the left.
5. Click **Download as .docx** and open the memo.

---

## Step 6 — Ongoing

**Updating the app.** Push to `main`; Community Cloud redeploys automatically.

**Changing the corpus.** Re-run `scripts/build_index_for_deploy.py`, then
`git add -f db/ && git commit && git push`. The index is a committed artifact, so it
only changes when you rebuild it.

**Changing secrets.** App menu (⋮) → **Settings** → **Secrets**. Saving reboots the app.
No redeploy needed.

**Sleeping.** Free apps sleep after a stretch of inactivity and wake on the next
visit — the first load after sleeping takes ~30 seconds. Nothing is lost, because
the index is in the repo rather than on the ephemeral disk.

**Cost control.** Every question a visitor asks bills your Anthropic key. Confirm the
Home page's Configuration panel reads *"🔒 password gate ON"* on the deployed app before
you share the URL. The password
gate is the main control. If you share the URL widely, consider rotating the password,
lowering `ANTHROPIC_MAX_TOKENS`, or switching `ANTHROPIC_MODEL` to a cheaper model.

---

## Troubleshooting

| Log message / symptom | Cause | Fix |
|---|---|---|
| `RuntimeError: Your system has an unsupported version of sqlite3` | `pysqlite3-binary` missing, or something imported chromadb before the shim | Confirm it is in `requirements.txt`; confirm each page has `import cloud_bootstrap` **above** `from config import …` |
| `ModuleNotFoundError: No module named 'pysqlite3'` on Windows, locally | The linux marker was removed | Keep `pysqlite3-binary; sys_platform == "linux"` |
| *"Argh. This app has gone over its resource limits"* | PyTorch crept back in, or ingestion ran on the cloud | Ensure `sentence-transformers` is **not** in `requirements.txt`; ensure `READ_ONLY = "true"` |
| `installer returned a non-zero exit code` | Python version mismatch on a wheel | Set Python **3.11** in Advanced settings and reboot |
| *"The prebuilt index is missing from this deployment"* | `db/` was never committed | `git add -f db/` — plain `git add` skips it |
| `ModuleNotFoundError: No module named 'config'` | Wrong main file path | It must be `app/Home.py` |
| `ANTHROPIC_API_KEY is not set` in the app | Secret missing or misspelled | Settings → Secrets; the key name is case-sensitive. Retrieval still works without it |
| Answers cite nothing / no chunks returned | Index built with a different backend than the app queries with | Rebuild via `scripts/build_index_for_deploy.py` (it forces `onnx`), recommit `db/` |
| Password prompt never appears | `APP_PASSWORD` is unset or blank | An unset password means an open app **by design**, so localhost does not nag you. Set `APP_PASSWORD` in `.env` locally, or in Streamlit **Secrets** when deployed. The Home page's **Configuration** panel shows which mode is active |
| `UnicodeDecodeError: 'charmap' codec can't decode byte ...` locally on Windows | A text file was read without naming an encoding; Windows defaults to cp1252 and the emoji in the pages break it | Already fixed — every read/write names `utf-8`, and the smoke test enforces it. If you add code, pass `encoding="utf-8"` |
| `Failed to send telemetry event ...: capture() takes 1 positional argument but 3 were given` | Cosmetic ChromaDB/PostHog signature mismatch; no data leaves your machine either way | Already silenced in `retrieval/store.py`. Harmless if you see it from another tool |

---

## If Community Cloud proves too tight

The 2.7 GB ceiling is the binding constraint. If you later add a larger embedding
model or a bigger corpus, the same repo deploys with almost no change to:

- **Hugging Face Spaces** (free tier, 16 GB) — add a `Dockerfile` or use the Streamlit SDK.
- **Render / Railway / Fly.io** — a persistent disk means you can drop `READ_ONLY`
  and ingest on the host.
- **Snowflake Streamlit** — if the data ever needs to live in a warehouse.

Nothing in the code is Community-Cloud-specific: `cloud_bootstrap.py` no-ops where the
shim is unnecessary, and `EMBEDDING_BACKEND=auto` picks PyTorch wherever it is installed.
