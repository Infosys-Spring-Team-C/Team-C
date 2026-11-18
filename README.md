# SalesGenie AI - Backend & Data Platform

Canonical repository for the Infosys Springboard Team-C project **SalesGenie AI - AI Sales
Assistant & Lead Intelligence Platform**.

This repository contains the **FastAPI backend, PostgreSQL schema and migrations, JWT/RBAC
security, the AI intelligence layer, the Streamlit frontend, Docker packaging and the test
suite**. The frontend's original design is owned by Maheksaba Akbar Shaikh; the current
peach-and-cream rewrite from the updated Team-C archive is integrated here on top of the
canonical API, with the outreach and intelligence controls re-applied.

> **Honesty statement.** This README distinguishes what is implemented and tested from what is
> planned. Every test result quoted below was produced by running the command shown. The default
> intelligence path is the merged **AI package** contributed by Mahidhar; with a Groq key it calls
> a live model and reports `used_mock=false`. Without a key it runs the package's deterministic
> mock provider and labels every result `used_mock=true`. The heuristic engine remains an explicit
> offline fallback. Neither engine ships a trained or calibrated model, and the API never presents
> one as calibrated.

---

## 1. Current status

| Area | Status | Evidence |
|---|---|---|
| Lead CRUD, lifecycle stages, filtering, pagination | Implemented, tested | `tests/test_api_leads.py` |
| CSV import with validation, duplicate policy, per-row reporting | Implemented, tested | `tests/test_api_import.py` |
| JWT authentication, RBAC (`admin`/`manager`/`rep`/`viewer`) | Implemented, tested | `tests/test_api_auth.py` |
| Company analysis / lead intelligence | Implemented; default AI package (external) | `tests/test_api_ai.py`, `tests/test_merge_integration.py` |
| Outreach generation + draft persistence + prompt controls | Implemented, tested; generate/refresh, edit, copy, save and record-as-sent in the UI | `tests/test_api_ai.py`, `tests/test_frontend_compat.py` |
| Email delivery | **Not implemented** - returns `501` by design (SRS D-05) | `POST /api/v1/outreach/send` |
| Lead scoring + explainable factors | Implemented; AI package maps 8 factors onto the 4 SRS dimensions | `tests/test_merge_integration.py`, `tests/test_api_ai.py` |
| Calibrated conversion probability | **Not implemented** - returns `null` | `lead_scores.conversion_probability` |
| Conversation summaries | Implemented; default AI package, heuristic fallback; stored in `sales_interactions` | `tests/test_api_ai.py` |
| Conversations UI | Implemented; meeting summary, CRM sync status, field mapping, recent-activity feed and history | `frontend/app.py`, `tests/test_frontend_compat.py` |
| Analytics + follow-ups | Implemented; undefined KPIs return `null` | `tests/test_api_ai.py` |
| CRM field mapping + sync audit | Implemented for contacts, activities and deal stages; provider-neutral simulator, optional live Salesforce/HubSpot transport, `crm_sync_logs` and retry. Live transport is **not yet verified against a real org** (SRS D-06) | `/api/v1/crm/*`, `backend/services/crm.py`, `backend/services/crm_transport.py`, `tests/test_crm_transport.py` |
| Alembic migration | Implemented, verified on SQLite and PostgreSQL 16 | `alembic/versions/0001_canonical_schema.py` |
| Docker packaging | Built and run with Docker 29.7.2: `db`, `api` and `frontend` all healthy; API migrated PostgreSQL | `Dockerfile`, `docker-compose.yml`, `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| CI workflow | Added 18 Nov 2026: SQLite suite, PostgreSQL 16 service, schema-drift check and committed-credential scan. **Not yet executed on GitHub** | `.github/workflows/ci.yml` |
| Streamlit frontend | Rewritten peach/cream UI integrated from the updated main archive; login, lead directory, intelligence, outreach studio, conversations and analytics; browser-verified (see `docs/qa/evidence/2026-11-18-browser-walkthrough.md`) | `frontend/`, `tests/test_frontend_compat.py`, `docs/today-review.md` |

Full details: [`docs/audit-report.md`](docs/audit-report.md),
[`docs/test-report.md`](docs/test-report.md),
[`docs/milestone-readiness.md`](docs/milestone-readiness.md).

---

## 2. Architecture

```
                    +---------------------------+
                    | Streamlit UI (frontend/)  |
                    +------------+--------------+
                                 | HTTP/JSON + Bearer JWT
                    +------------v--------------+
                    |      FastAPI backend      |
                    |  routers/  (HTTP layer)   |
                    |  services/ (domain logic) |
                    |  intelligence/ (AI port)  |
                    +------+-------------+------+
                           |             |
             SQLAlchemy ORM|             |IntelligenceEngine protocol
                    +------v------+   +--v---------------------------+
                    | PostgreSQL  |   | ExternalAIEngine (default)   |
                    | 8 tables    |   |  -- ai.* package, auto       |
                    |             |   |     provider selection       |
                    |             |   | HeuristicEngine (fallback)   |
                    +-------------+   +------------------------------+
```

Design rules enforced by the code:

* Routers never import an LLM SDK or an agent graph. They depend on
  `backend.intelligence.contract.IntelligenceEngine`.
* `SALES_GENIE_AI_BACKEND=external` (default) always uses the merged AI package and fails loudly
  if it is missing or returns invalid output. `auto` uses the package when importable and falls
  back to the deterministic heuristic only when it is not; `heuristic` forces the offline engine.
* `SALES_GENIE_LLM_PROVIDER=auto` (default) uses Groq when `GROQ_API_KEY` is set, OpenAI when
  `OPENAI_API_KEY` is set, Gemini when `GOOGLE_API_KEY` is set, and otherwise the package's
  deterministic mock provider. The health endpoint and every execution record expose `used_mock`,
  so demo output is labelled honestly.
* The adapter `backend/intelligence/external.py` integrates the reviewed `ai.*` package without
  copying it. It forwards channel, tone, length, goal, pain points, product and CTA, and maps the
  package's eight score factors onto the four SRS FR-030 dimensions.
* Generation and delivery are separate. Nothing in this repository can send an email.
* Scores are stored with their factor breakdown; conversion probability is `NULL` unless a
  calibrated model exists.

---

## 3. Directory structure

```
Team-C/
|-- main.py                     # uvicorn entry point (main:app)
|-- backend/
|   |-- api.py                  # application factory, health, CORS, error handlers
|   |-- config.py               # environment-driven settings (no defaults for secrets)
|   |-- db.py                   # 8 SQLAlchemy models, engine/session, lifecycle vocabulary
|   |-- schemas.py              # Pydantic request/response models
|   |-- security.py             # PBKDF2 password hashing, JWT issue/verify
|   |-- deps.py                 # current-user dependency + RBAC factories
|   |-- errors.py               # consistent error envelope
|   |-- cli.py                  # create-user / init-db / seed-demo
|   |-- routers/                # auth, leads, intelligence, outreach, scoring, conversations, analytics
|   |-- services/               # lead rules, CSV import, analytics
|   `-- intelligence/           # contract.py, heuristic.py, external.py
|-- alembic/
|   |-- env.py                  # DATABASE_URL always from settings
|   `-- versions/0001_canonical_schema.py
|-- tests/                      # backend + AI + frontend-adapter tests
|-- scripts/                    # render_db_workspace.py, qa_uat.py, qa_conversations_render.py,
|                               #   check_ai_integration.py, check_frontend_integration.py
|-- ai/                         # AI package (Mahidhar): graph, agents, prompts, providers, scoring
|-- frontend/                   # Streamlit UI (Maheksaba) + api_compat.py adapter
|-- salesgenie-db-workspace/    # generated PostgreSQL baseline, ER diagram, DB-only Compose
|-- docs/                       # SRS, audit, reviews, API contract, reports
|-- requirements.txt
|-- requirements-dev.txt
|-- Dockerfile
|-- docker-compose.yml
`-- .env.example
```

---

## 4. Quick start (SQLite, no Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

Copy-Item .env.example .env
# Edit .env: set JWT_SECRET to a long random value.
# For a quick local run you may set DATABASE_URL=sqlite:///./salesgenie.db

python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET

python -m alembic upgrade head
python -m backend.cli create-user --email lead@example.com --role admin
uvicorn main:app --reload
```

Then open <http://127.0.0.1:8000/docs> for interactive OpenAPI documentation.

The CLI prompts for the password; it is never echoed and never committed.

### First authenticated request

```powershell
$token = (Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/token `
  -Body @{ username = "lead@example.com"; password = "..." }).access_token

Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/leads `
  -Headers @{ Authorization = "Bearer $token" }
```

---

## 5. PostgreSQL and migrations

The canonical database is PostgreSQL 16. `DATABASE_URL` must use the `psycopg` driver:

```
DATABASE_URL=postgresql+psycopg://salesgenie:YOUR_PASSWORD@localhost:5432/salesgenie
```

```powershell
python -m alembic upgrade head     # apply the canonical schema
python -m alembic current          # show the applied revision
python -m alembic downgrade base   # destructive; development only
```

The migration creates exactly eight tables:

`users`, `leads`, `company_insights`, `outreach_campaigns`, `lead_scores`,
`sales_interactions`, `crm_sync_logs`, `sales_analytics`.

Schema changes must be added as new Alembic revisions. `Base.metadata.create_all()` is used only
by the test suite and `backend.cli init-db`.

---

## 6. Docker Compose

```powershell
Copy-Item .env.example .env
# Set POSTGRES_PASSWORD and JWT_SECRET in .env
docker compose up --build
```

Compose starts PostgreSQL 16 with a persistent named volume, the API and the Streamlit
frontend. The API container waits for the database health check, runs `alembic upgrade head`,
then starts uvicorn. Ports 8000 (API) and 8501 (UI) are published, bound to `127.0.0.1`.

This stack was **built and started** on 27 October 2026 with Docker 29.7.2; all three
services reported healthy and the API migrated PostgreSQL. Create the first login with
`docker compose exec api python -m backend.cli create-user --email you@example.com --role admin`
and set `FRONTEND_BACKEND_EMAIL` / `FRONTEND_BACKEND_PASSWORD` in `.env` for the UI. See
`docs/qa/evidence/2026-10-27-docker-compose-verification.txt`.

---

## 7. API summary

Base prefix: `/api/v1`. All endpoints except `POST /auth/token` and `GET /health` require
`Authorization: Bearer <token>`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/token` | OAuth2 password login |
| GET | `/auth/me` | Current user |
| GET/POST | `/auth/users` | List/create users (admin) |
| PATCH | `/auth/users/{id}` | Change role/active flag (admin) |
| POST/GET | `/leads` | Create / list leads |
| GET/PATCH/DELETE | `/leads/{id}` | Retrieve / update / delete |
| POST | `/leads/duplicate-check` | Duplicate lookup |
| POST | `/leads/import` | CSV import with report |
| POST/GET | `/leads/{id}/insights` | Generate / list company intelligence |
| POST | `/outreach/generate` | Generate and persist a draft |
| POST | `/outreach/send` | Always `501` (no transport) |
| GET/POST | `/leads/{id}/outreach-drafts` | List / save drafts |
| GET/PATCH | `/outreach/campaigns/{id}` | Read / edit a draft |
| POST | `/outreach/campaigns/{id}/mark-sent` | Record manual sending |
| POST/GET | `/leads/{id}/scores` | Score / score history |
| GET | `/leads/{id}/scores/latest` | Latest score |
| POST | `/leads/{id}/conversations` | Save a summary |
| GET | `/leads/{id}/conversations` | List interactions |
| POST | `/conversations/summarize` | Summarise a transcript |
| GET | `/conversations/{id}` | Read one interaction |
| GET | `/analytics` | Dashboard metrics |
| POST | `/analytics/insights` | Interpret supplied aggregates |
| POST | `/analytics/snapshot` | Persist a metrics snapshot (manager) |
| GET | `/follow-ups` | Recommendations from stored scores |
| GET | `/recommendations/{lead_id}` | Per-lead recommendation |
| GET | `/crm/providers` | Configuration state |
| GET | `/crm/field-mappings` | Documented Salesforce/HubSpot field map |
| POST | `/crm/mappings/validate` | Validate a field mapping |
| POST | `/crm/sync/preview` | Dry-run export |
| POST | `/crm/sync` | `501` without `simulate`; labelled simulated sync with it |
| GET | `/crm/sync-logs` | Sync history, including entity type and outcome |
| POST | `/crm/sync-logs/{id}/retry` | Increment attempt, returns failure |
| GET | `/health` | Liveness/readiness summary |

Full request/response documentation: [`docs/api-contract.md`](docs/api-contract.md).

---

## 8. AI provider configuration

```env
SALES_GENIE_AI_BACKEND=external         # external (default) | auto | heuristic
SALES_GENIE_LLM_PROVIDER=groq           # auto | groq | mock | openai | gemini
SALES_GENIE_LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=                           # private; never commit
GROQ_BASE_URL=https://api.groq.com/openai/v1
GOOGLE_API_KEY=
OPENAI_API_KEY=
```

* `external` is the default product path: the AI package is included in this repository and is
  always used. A missing package or invalid structured output produces `502 ai_failed`, never a
  silent fallback. Install the package's extras with `pip install -r ai/requirements.txt`.
* With `auto` and no provider key, the **AI package still runs** through its deterministic mock
  provider. Every execution is labelled `used_mock=true`; the UI shows a warning and the health
  endpoint reports `ai_mode=offline-mock`.
* With a Groq key present (`GROQ_API_KEY`), `auto` selects Groq's OpenAI-compatible endpoint
  and a JSON-mode open-weight model (`openai/gpt-oss-120b` by default). This environment is
  configured that way: the health endpoint reports `ai_provider=groq`,
  `ai_mode=live-model`, `ai_used_mock=false`. OpenAI and Gemini remain selectable with their
  own keys and are **not** verified here. The backend validates the AI package's structured
  output against its own Pydantic contract.
* `auto` as an *engine* uses the AI package when importable and falls back to the heuristic only
  when it is not; `heuristic` forces the offline deterministic engine and is kept as a tested
  fallback. It is never selected silently while the live provider is configured.
* `SALES_GENIE_LLM_PROVIDER=grok` is accepted as a historical alias for `groq`; the canonical
  provider name reported by the health endpoint is `groq`.
* The AI integration gate is `python scripts/check_ai_integration.py`; it exercises all six
  operations and prints `6/6 operations passed`. The live Groq run was repeated on
  17 November 2026 with the optional `openai` SDK installed: every operation reported
  `used_mock=False` (evidence:
  `docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt`). Without the SDK the gate
  exits `2` with an actionable SKIP rather than pretending to pass.
* Attribution and the list of maintainer corrections: [`docs/ai-handoff.md`](docs/ai-handoff.md),
  [`CREDITS.md`](CREDITS.md).

---

## 9. Tests

```powershell
# SQLite-backed suite (no external services required)
$env:JWT_SECRET = "unit-test-secret-value-0123456789"
python -m pytest -q

# Include real PostgreSQL integration tests
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q
```

Verified results:

* SQLite only (18 November 2026): **191 passed, 7 skipped** - 6 PostgreSQL-only tests and 1
  opt-in LangGraph test. This includes the 16 CRM live-transport tests added on 18 November,
  the expanded frontend adapter/login/normaliser tests, the intelligence package tests, the
  Groq provider tests and the merge-integration tests. The 17 November run was 175 passed,
  7 skipped before the transport tests existed.
* With PostgreSQL 16 (6 November 2026): **177 passed, 0 skipped**, including schema,
  migration up/down and dialect-parity checks.

The PostgreSQL module refuses to run unless the database name contains `test`, and it drops and
recreates the `public` schema. Exact commands and output: [`docs/test-report.md`](docs/test-report.md).

### QA / test-engineering pack

The full QA deliverables for the milestone - test plan, scenarios, 81 test cases, traceability
matrix, API and database matrices, AI quality validation, regression procedure, defect log,
UAT plan and results, and the milestone test reports - are in
[`docs/qa/`](docs/qa/README.md). Every result there is backed by a captured artifact in
[`docs/qa/evidence/`](docs/qa/evidence/).

A live acceptance run against a real server is also reproducible:

```powershell
python scripts/qa_uat.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"
```

Verified result: **25 of 25 workflows passed, 0 partial, 0 failed** (17 November 2026). The
Module 5 workflows cover CRM field mappings, the three simulated syncs, a rejected operation
and the Conversations data contract. The page is additionally rendered headlessly against the
same server with `scripts/qa_conversations_render.py` (PASS - 7 sections).

### Database deployment baseline

[`salesgenie-db-workspace/`](salesgenie-db-workspace/README.md) holds the portable PostgreSQL
DDL, the ER diagram and a database-only Compose file. Both generated files are derived from
`backend/db.py`, so they cannot drift:

```powershell
python scripts/render_db_workspace.py --check   # exits 1 if a file is stale
```

The generated DDL and the Alembic migration were applied to two empty PostgreSQL 16 databases
and compared object by object: identical 110 columns, 6 foreign keys and 31 indexes. Evidence:
[`docs/qa/evidence/2026-10-26-schema-parity.txt`](docs/qa/evidence/2026-10-26-schema-parity.txt).

---

## 10. Known limitations

1. **No email delivery.** `POST /outreach/send` returns `501`. Drafts can be generated, edited and
   marked as sent manually.
2. **No calibrated conversion model.** `conversion_probability` is `NULL` for every score,
   including the default external/rule-based path. The returned `probability_band` is explicitly
   labelled uncalibrated and the UI prints "No calibrated model configured".
3. **Undefined KPIs are `null`.** `pipeline_value`, `average_response_time_days` and
   `average_sales_cycle_days` require decisions the schema cannot yet support (SRS D-10).
4. **No verified live CRM sync.** Field maps for Salesforce and HubSpot are documented, dry-run
   previews work, and a clearly-labelled simulator covers contact, activity and deal-stage
   workflows while writing `crm_sync_logs`. A live transport is implemented
   (`backend/services/crm_transport.py`) and is opt-in: it needs `CRM_LIVE_ENABLED=true` plus
   provider credentials, retries `429`/`5xx` with backoff, and records a `mode: live` audit row.
   It has **not** been exercised against a real Salesforce org or HubSpot portal, so `FR-041`
   and `FR-042` stay `PARTIAL` until a sandbox run is captured.
5. **Live Groq calls are verified; OpenAI and Gemini are not.** The AI path runs the full agent
   workflow through Groq's OpenAI-compatible endpoint with `used_mock=false` when `GROQ_API_KEY`
   is configured. Without a key it uses the deterministic mock provider and reports
   `ai_mode=offline-mock`. OpenAI and Gemini remain unverified.
6. **Docker verified locally, not production-hardened.** The Compose stack builds and runs, but
   there is no TLS termination, secrets manager or orchestrator configuration.
7. **CI workflow added, not yet observed running.** `.github/workflows/ci.yml` runs the SQLite
   suite, the PostgreSQL 16 suite against a service container, the schema-drift check and a
   credential scan. It has not been executed on GitHub yet, so no green badge is claimed.
8. **No formal human usability acceptance of the UI.** The rewritten frontend was exercised in a
   browser end to end (generate, regenerate, save, record-as-sent, dispatch refusal, score,
   analyse, summarise, insights) and its adapter tests pass; the eight UI requirements have not
   been formally signed off by a person. See [`docs/today-review.md`](docs/today-review.md).
9. **Follow-ups are read-only.** There is no dismissal endpoint (BUG-011). FR-052 only requires
   the panel, which works.

---

## 11. Attribution and contribution workflow

This repository is the only source of truth. Individual repositories are review targets:

* `Infosys-Spring-Team-C/team_c_sai` - database/DevOps work. **Merged** on 26 October 2026
  with `--no-ff` and without squashing, so commit `d4f7fd7` remains authored by
  `saisurekha914 <saisurekha914@gmail.com>`. The canonical schema was reconciled against her
  workspace in separate lead commits; the record is
  [`docs/database-merge-notes.md`](docs/database-merge-notes.md).
* `Infosys-Spring-Team-C/team-c-doran` - backend contract and CRM work by **M Doran**. The
  canonical backend is retained, but his provider-neutral CRM payload mapping, deterministic
  simulator and CRM status endpoint are merged and adapted in `backend/services/crm.py` and
  `backend/routers/analytics.py`. Merge record: [`CREDITS.md`](CREDITS.md),
  [`docs/merge-report.md`](docs/merge-report.md).
* `mahidar22/infosys-springboard-internship` - AI/ML work. **Merged** on 27 October 2026.
  The contributor could not push a branch, so his submitted archive was applied with him as
  git **author** (`Mahidhar Reddy <mahidarreddy.2005@gmail.com>`) and the lead as
  **committer**. Integration corrections are separate lead commits. Review:
  [`docs/ai-review.md`](docs/ai-review.md); disclosure and correction list:
  [`docs/ai-handoff.md`](docs/ai-handoff.md).
* `Mahek-saba/frontend-infosys` - Streamlit frontend. Her original UI was merged from the
  `frontend-ui` branch; the updated peach-and-cream rewrite delivered in the latest Team-C main
  archive is the current UI baseline. Integration work (API adapter, packaging, outreach and
  intelligence controls, browser verification) is separate maintainer work. See
  [`docs/frontend-merge-notes.md`](docs/frontend-merge-notes.md) and
  [`docs/today-review.md`](docs/today-review.md).

The core backend implementation in this repository was authored by Mohamed Isharak M under his own
Git identity. The CRM mapping/simulator and the AI package are credited to their contributors in
[`CREDITS.md`](CREDITS.md); no contributor's work is presented as the maintainer's own.

---

## 12. Documentation index

| Document | Contents |
|---|---|
| [`CREDITS.md`](CREDITS.md) | Contributor attribution and what each person's merged work covers |
| [`docs/merge-report.md`](docs/merge-report.md) | Consolidation of the backend, AI/DevOps, database and frontend work |
| [`docs/today-review.md`](docs/today-review.md) | Milestone 2 review demo script and verification commands |
| [`docs/SRS.md`](docs/SRS.md) | Authoritative requirements (FR/NFR, decisions) |
| [`docs/audit-report.md`](docs/audit-report.md) | Audit of all three repositories |
| [`docs/database-review.md`](docs/database-review.md) | File-specific review for Sai |
| [`docs/ai-review.md`](docs/ai-review.md) | File-specific review for Mahidhar |
| [`docs/ai-handoff.md`](docs/ai-handoff.md) | AI attribution disclosure and maintainer corrections |
| [`docs/api-contract.md`](docs/api-contract.md) | Routes, schemas, auth, errors |
| [`docs/frontend-integration.md`](docs/frontend-integration.md) | Frontend contract and page-to-endpoint map |
| [`docs/frontend-merge-notes.md`](docs/frontend-merge-notes.md) | What was merged from Maheksaba, patches, verification |
| [`docs/test-report.md`](docs/test-report.md) | Exact commands and results |
| [`docs/git-report.md`](docs/git-report.md) | Branch, commits, push status |
| [`docs/pr-description.md`](docs/pr-description.md) | Ready-to-use pull request description |
| [`docs/contributor-actions.md`](docs/contributor-actions.md) | Actions for Sai and Mahidhar |
| [`docs/pr-changes.md`](docs/pr-changes.md) | Exact file-level changes and commands per contributor |
| [`docs/milestone-readiness.md`](docs/milestone-readiness.md) | What can be demonstrated |
| [`docs/presentations/devops-database/presentation.md`](docs/presentations/devops-database/presentation.md) | Database / DevOps Milestone 3 write-up: schema design, Module 5 tables, drift control, deployment and evidence |
| [`docs/presentations/qa/presentation.md`](docs/presentations/qa/presentation.md) | QA Milestone 3 write-up: test approach, Module 5 coverage, UAT, UI verification, defects and evidence |
| [`docs/database-merge-notes.md`](docs/database-merge-notes.md) | Merge of the database contributor's branch and the column-by-column reconciliation |
| [`salesgenie-db-workspace/README.md`](salesgenie-db-workspace/README.md) | Database deployment baseline: DDL, ER diagram, DB-only Compose |
| [`docs/qa/README.md`](docs/qa/README.md) | QA pack index: plan, cases, matrices, defects, UAT, milestone report |
| [`docs/qa/milestone-test-report.md`](docs/qa/milestone-test-report.md) | Headline test report for the Milestone 2 review |
| [`docs/qa/milestone3-test-report.md`](docs/qa/milestone3-test-report.md) | Milestone 3 test report for Module 5 (conversations and CRM) |
| [`docs/reports/Milestone 3 report - Backend.md`](docs/reports/Milestone%203%20report%20-%20Backend.md) | Milestone 3 backend completion report for Module 5 |
| [`docs/reports/Milestone 3 report - QA.md`](docs/reports/Milestone%203%20report%20-%20QA.md) | Milestone 3 QA completion report for Module 5 |
| [`docs/reports/Milestone 3 report - DevOps and Database.md`](docs/reports/Milestone%203%20report%20-%20DevOps%20and%20Database.md) | Milestone 3 database and deployment completion report for Module 5 |
| [`docs/qa/bug-log.md`](docs/qa/bug-log.md) | 20 defects with severity, reproduction and status |
| [`docs/qa/traceability-matrix.md`](docs/qa/traceability-matrix.md) | FR/AC to test case to automated test |
| [`postman/SalesGenie-AI.postman_collection.json`](postman/SalesGenie-AI.postman_collection.json) | 46-request Postman collection |
