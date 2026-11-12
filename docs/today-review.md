# Milestone 2 review guide

Date: 5 November 2026
Project: **SalesGenie AI - AI Sales Assistant & Lead Intelligence Platform** (Infosys Springboard Team C)

This is the runbook for today's review. It lists exactly what to start, what to click, what the
screen should show, and which claims are deliberately *not* made. Every command and number below
was executed on this machine on the date above.

---

## 1. What is in this build

| Capability | State |
|---|---|
| Lead CRUD, lifecycle stages, filtering, pagination | Implemented and tested |
| CSV import with per-row reporting and duplicate policy | Implemented and tested |
| JWT login and RBAC (`admin` / `manager` / `rep` / `viewer`) | Implemented and tested |
| Company analysis / lead intelligence | Implemented via the merged AI package |
| Lead scoring with an explainable factor breakdown | Implemented; 8 package factors aggregated onto the 4 SRS dimensions |
| Calibrated conversion probability | **Not implemented** - always `null`, labelled uncalibrated |
| Outreach generation with tone, length, channel, goal, product, CTA and pain points | Implemented; generate and regenerate a variation |
| Outreach editing, copy, save draft, record as sent | Implemented in the UI and API |
| Email delivery | **Not implemented** - `POST /api/v1/outreach/send` returns `501` by design (SRS D-05) |
| Conversation summaries and history | Implemented |
| Analytics, follow-ups and narrative insights | Implemented; undefined KPIs return `null` |
| CRM mapping, dry-run simulator and failure logging | Implemented; no live CRM transport (SRS D-06) |
| Streamlit UI | Rewritten peach-and-cream UI, integrated on the canonical API |
| Docker packaging | Present; the verified run recorded in `docs/qa/evidence/` used PostgreSQL 16 |

### Honest caveats

1. **A Groq key is configured and live-verified.** The default engine is the merged AI package
   (`external`) with `SALES_GENIE_LLM_PROVIDER=groq`, using `openai/gpt-oss-120b` through Groq's
   OpenAI-compatible endpoint. All six operations and a live outreach draft completed with
   `used_mock=false`. The deterministic **mock** provider and the offline heuristic engine remain
   selectable fallbacks. OpenAI and Gemini calls are **not** verified.
2. **No calibrated conversion model.** `conversion_probability` stays `null`. The UI shows
   "No calibrated model configured" rather than inventing a number.
3. **No email transport.** "Record as sent" only changes the draft status; "Attempt dispatch"
   returns a truthful `501` explanation.
4. **No git history or push in this environment.** The `git` binary and GitHub credentials are not
   available, so the deliverable is a source bundle produced from this working tree.

---

## 2. Start the application (Linux, from the project root)

```bash
cd "/home/isharak7m/Documents/Default Project"

# One-time setup (already done in the prepared environment)
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
# Set JWT_SECRET and DATABASE_URL=sqlite:///./salesgenie.db in .env

# Reset a clean demo database
rm -f salesgenie.db
./.venv/bin/python -m backend.cli init-db
./.venv/bin/python -m backend.cli create-user \
  --email demo.lead@example.com --role rep --full-name "Demo Lead" \
  --password 'DemoPass123!'
./.venv/bin/python -m backend.cli seed-demo --confirm

# Terminal 1 - API
./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2 - UI
set -a && . ./.env && set +a
./.venv/bin/python -m streamlit run frontend/app.py \
  --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

Open <http://127.0.0.1:8501> and sign in with:

```
demo.lead@example.com
DemoPass123!
```

API documentation: <http://127.0.0.1:8000/docs>

### Expected health output

```bash
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
```

```json
{
  "status": "ok",
  "database": "ok",
  "database_dialect": "sqlite",
  "auth_enabled": true,
  "ai_backend": "external",
  "ai_provider": "groq",
  "ai_model": "openai/gpt-oss-120b",
  "ai_used_mock": false,
  "ai_mode": "live-model",
  "ai_note": "",
  "ai_status": "ok"
}
```

The same state is visible in the UI header and sidebar: **Backend connected**, scoring engine
External, live provider `groq · openai/gpt-oss-120b`, and `used_mock=false`.

The six seeded leads are clearly labelled fictional demo records (Northwind Logistics, Contoso
Manufacturing, Fabrikam Retail, InnovateAI Labs, Bluebird Health, Vanguard Fintech).

---

## 3. Demo script (about 8 minutes)

### Step 1 - Overview

* Land on **Overview**.
* Point out the KPI strip: 6 prospects, 3 qualified, average score, conversion rate.
* Point out the AI status card: engine **External**, provider **groq**, model
  `openai/gpt-oss-120b`, `used_mock=false`. This is the honesty story: the live model is called
  and the provider/model are reported per execution.

### Step 2 - Leads

* Open **Leads**. The directory lists all six prospects, with import and add-lead controls.
* The directory is the single source of truth; no data is invented in the UI.

### Step 3 - Lead Intelligence

* Open **Lead Intelligence**, select a prospect.
* Click **Analyse company**. Show the split between **supplied facts** and **generated
  hypotheses**, and the explicit "no external website retrieval was performed" note.
* Click **Compute score**. Show the score, qualification band, factor breakdown and the
  **conversion probability `n/a`** with the uncalibrated-methodology caption.
* The recommended next action is stored with the score.

### Step 4 - Outreach Studio (the centrepiece)

* Open **Outreach Studio**, choose a prospect.
* Show the controls: **Tone**, **Length**, **Channel**, **Goal**, **Product / service**,
  **Industry context**, **Call to action**, **Known pain points**.
* Click **Generate draft**. A subject and body appear, with a caption such as:
  `Draft #N · status draft · engine external · provider groq · model openai/gpt-oss-120b`
  and `used_mock=false`.
* Click **Regenerate variation** and show that the wording changes while staying on the same
  prospect and settings.
* Edit the subject or body. Click **Copy message** to reveal the copy-ready text.
* Click **Save draft**. The confirmation appears and the status stays `draft`.
* Click **Record as sent**. The status becomes `sent` and the message states that **no email was
  transmitted**.
* Click **Attempt dispatch**. The UI reports **Not sent** and explains that no delivery provider
  is configured (the API returns `501`). This is deliberate, not a failure to hide.
* Click **Load recommendation** to show priority, timing, channel and the suggested follow-up.

### Step 5 - Conversations

* Open **Conversations**, paste a short transcript and click **Summarise**.
* Show the summary, suggested follow-up and the saved history entry. The live model summarises
  only the supplied transcript and leaves dates or owners empty when they are not explicit.

### Step 6 - Analytics

* Open **Analytics**. Show pipeline distribution, qualification bands, activity trend and
  follow-ups.
* Click **Generate insights**. Show that every observation cites backend-supplied evidence and
  that the caveat says observations do not establish causes or forecast results.

### Step 7 - Close

* Restate the three boundaries: the AI package runs against a live Groq model (OpenAI/Gemini
  unverified); conversion probability is `null` because no calibrated model exists; email
  delivery is `501` because no transport is configured.

---

## 4. Verification commands

```bash
# Full automated suite (SQLite; PostgreSQL module self-skips)
python -m pytest -q
# expected: 171 passed, 6 skipped

# With PostgreSQL 16 available:
# TEST_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/salesgenie_test
# expected: 177 passed, 0 skipped

# AI integration gate over all six operations
./.venv/bin/python scripts/check_ai_integration.py
# expected: 6/6 operations passed, provider=groq, used_mock=False

# Database workspace drift check
./.venv/bin/python scripts/render_db_workspace.py --check
```

The browser checks performed for this review covered: login, Overview, Leads, Lead Intelligence
(analyse + score), Outreach Studio (generate, regenerate, edit, copy, save, record-as-sent,
dispatch refusal, recommendation), Conversations (summarise + history) and Analytics (insights).
No console errors appeared on those pages.

---

## 5. Architecture in one minute

```
Streamlit UI (frontend/)  ->  frontend/api_compat.py  ->  FastAPI /api/v1
                                                          |
                                       backend/intelligence/contract.py
                                                          |
                                    ExternalAIEngine (default) -> ai/ package
                                    HeuristicEngine (explicit fallback)
                                                          |
                                                SQLAlchemy -> PostgreSQL/SQLite
```

* Routers never import an LLM SDK; they depend on the `IntelligenceEngine` protocol.
* `SALES_GENIE_AI_BACKEND=external` is the default and fails loudly if the package is missing.
* `SALES_GENIE_LLM_PROVIDER=auto` selects Groq, then OpenAI, then Gemini when their keys exist,
  otherwise the package's deterministic mock provider.
* Generation and delivery are separate code paths. Nothing in the repository can send email.
* Scores persist their factor breakdown. `conversion_probability` remains `null`.

---

## 6. Configuration reference

```env
SALES_GENIE_AI_BACKEND=external     # external (default) | auto | heuristic
SALES_GENIE_LLM_PROVIDER=groq       # auto | groq | mock | openai | gemini
SALES_GENIE_LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=                       # private; never committed
OPENAI_API_KEY=                     # optional; enables live OpenAI via auto
GOOGLE_API_KEY=                     # optional; enables live Gemini via auto
DATABASE_URL=sqlite:///./salesgenie.db
JWT_SECRET=<long random value>
```

The current environment sets `SALES_GENIE_LLM_PROVIDER=groq` and keeps `GROQ_API_KEY` only in
`.env`. The health card reports `ai_provider=groq`, `ai_mode=live-model` and `ai_used_mock=false`.
Set `SALES_GENIE_LLM_PROVIDER=heuristic` with `SALES_GENIE_AI_BACKEND=heuristic` to run the
offline deterministic engine instead.

---

## 7. Attribution

* **Mohamed Isharak M** - canonical backend, integration, packaging and this review build.
* **M Doran** - provider-neutral CRM payload mapping, deterministic simulator and CRM status
  endpoint, adapted into `backend/services/crm.py` and `backend/routers/analytics.py`.
* **Mahidhar Reddy** - the `ai/` package: agents, graph, prompts, providers and scoring, with
  maintainer corrections recorded in `docs/ai-handoff.md`.
* **Saisurekha** - database/DevOps workspace baseline (`salesgenie-db-workspace/`), reconciled
  against the canonical schema in `docs/database-merge-notes.md`.
* **Maheksaba Akbar Shaikh** - original Streamlit frontend design; the updated peach-and-cream
  rewrite from the latest Team-C main archive is the current UI baseline.

See `CREDITS.md` and `docs/merge-report.md` for the file-level record.

---

## 8. Distributing this build

The prepared archive contains the source tree, documentation, tests, AI package, database
workspace and the Docker files. It intentionally excludes the virtual environment, local
database, secrets in `.env`, and caches.

Because `git` and GitHub credentials are unavailable on this machine, the archive is the
deliverable. To publish later:

```bash
git init
git add .
git commit -m "Milestone 2 review build"
git remote add origin https://github.com/Infosys-Spring-Team-C/Team-C.git
git push origin main
```

Review the archive's README for the exact bundle name and checksum.
