# SalesGenie AI - Backend & Data Platform

Canonical repository for the Infosys Springboard Team-C project **SalesGenie AI - AI Sales
Assistant & Lead Intelligence Platform**.

This repository currently contains the **FastAPI backend, PostgreSQL schema and migrations,
JWT/RBAC security, a deterministic intelligence layer, Docker packaging and the test suite**.
The Streamlit frontend is owned by Maheksaba Akbar Shaikh and will be integrated later through
her own pull request; no replacement UI is included here.

> **Honesty statement.** This README distinguishes what is implemented and tested from what is
> planned. Every test result quoted below was produced by running the command shown. The default
> intelligence engine is a **deterministic heuristic, not a trained or calibrated model**, and the
> API never presents it as one.

---

## 1. Current status

| Area | Status | Evidence |
|---|---|---|
| Lead CRUD, lifecycle stages, filtering, pagination | Implemented, tested | `tests/test_api_leads.py` |
| CSV import with validation, duplicate policy, per-row reporting | Implemented, tested | `tests/test_api_import.py` |
| JWT authentication, RBAC (`admin`/`manager`/`rep`/`viewer`) | Implemented, tested | `tests/test_api_auth.py` |
| Company analysis / lead intelligence | Implemented on the heuristic engine, tested | `tests/test_api_ai.py`, `tests/test_intelligence.py` |
| Outreach generation + draft persistence | Implemented, tested | `tests/test_api_ai.py` |
| Email delivery | **Not implemented** - returns `501` by design (SRS D-05) | `POST /api/v1/outreach/send` |
| Lead scoring + explainable factors | Implemented as heuristic, tested | `tests/test_api_ai.py` |
| Calibrated conversion probability | **Not implemented** - returns `null` | `lead_scores.conversion_probability` |
| Conversation summaries | Implemented on the heuristic engine, tested | `tests/test_api_ai.py` |
| Analytics + follow-ups | Implemented; undefined KPIs return `null` | `tests/test_api_ai.py` |
| CRM synchronisation transport | **Not implemented** - dry-run + failure logging only (SRS D-06) | `/api/v1/crm/*` |
| Alembic migration | Implemented, verified on SQLite and PostgreSQL 16 | `alembic/versions/0001_canonical_schema.py` |
| Docker packaging | Files complete and `docker compose config` validated; image **not built** here because the Docker daemon was unavailable | `Dockerfile`, `docker-compose.yml` |
| Streamlit frontend | Pending Maheksaba's PR | - |

Full details: [`docs/audit-report.md`](docs/audit-report.md),
[`docs/test-report.md`](docs/test-report.md),
[`docs/milestone-readiness.md`](docs/milestone-readiness.md).

---

## 2. Architecture

```
                    +---------------------------+
                    |  Streamlit UI (later PR)  |
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
                    | PostgreSQL  |   | HeuristicEngine (default)    |
                    | 8 tables    |   | ExternalAIEngine (adapter)   |
                    +-------------+   +------------------------------+
```

Design rules enforced by the code:

* Routers never import an LLM SDK or an agent graph. They depend on
  `backend.intelligence.contract.IntelligenceEngine`.
* The default engine is deterministic and offline, so the API is runnable and testable without
  credentials.
* The adapter `backend/intelligence/external.py` integrates the reviewed `ai.*` package without
  copying it. It is only activated with `SALES_GENIE_AI_BACKEND=external` after that PR is merged.
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
|-- tests/                      # 117 tests (111 SQLite + 6 PostgreSQL-gated)
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

Compose starts PostgreSQL 16 with a persistent named volume and the API. The API container waits
for the database health check, runs `alembic upgrade head`, then starts uvicorn. Only port 8000 is
published, bound to `127.0.0.1`.

`docker compose config` was validated in this environment. **The image was not built here** because
the Docker daemon was not running; see `docs/test-report.md` for the exact blocker.

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
| POST | `/crm/mappings/validate` | Validate a field mapping |
| POST | `/crm/sync/preview` | Dry-run export |
| POST | `/crm/sync` | Records failure, returns `501` |
| GET | `/crm/sync-logs` | Sync history |
| POST | `/crm/sync-logs/{id}/retry` | Increment attempt, returns failure |
| GET | `/health` | Liveness/readiness summary |

Full request/response documentation: [`docs/api-contract.md`](docs/api-contract.md).

---

## 8. AI provider configuration

```env
SALES_GENIE_AI_BACKEND=heuristic        # default; offline and deterministic
# SALES_GENIE_AI_BACKEND=external       # requires the reviewed ai.* package (PR pending)
SALES_GENIE_LLM_PROVIDER=mock           # mock | grok | gemini | openai
SALES_GENIE_LLM_MODEL=
GROK_API_KEY=
GOOGLE_API_KEY=
OPENAI_API_KEY=
```

* With `heuristic`, no network calls and no credentials are needed. Outputs are labelled
  `heuristic` in the `execution` block and `provider`/`model` columns.
* With `external`, the backend validates the AI package's structured output against its own
  Pydantic contract. Missing package or invalid output produces `502 ai_failed`, never a silent
  fallback.
* The external adapter is **untested end to end** here because the AI package has not been merged.
  See [`docs/ai-review.md`](docs/ai-review.md).

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

Verified results in this environment:

* SQLite only: **111 passed, 6 skipped** (the PostgreSQL module skips itself).
* With PostgreSQL 16 on `127.0.0.1:55432`: **117 passed**.

The PostgreSQL module refuses to run unless the database name contains `test`, and it drops and
recreates the `public` schema. Exact commands and output: [`docs/test-report.md`](docs/test-report.md).

---

## 10. Known limitations

1. **No email delivery.** `POST /outreach/send` returns `501`. Drafts can be generated, edited and
   marked as sent manually.
2. **No calibrated conversion model.** `conversion_probability` is `NULL` for heuristic scores.
   The returned `probability_band` is explicitly labelled uncalibrated.
3. **Undefined KPIs are `null`.** `pipeline_value`, `average_response_time_days` and
   `average_sales_cycle_days` require decisions the schema cannot yet support (SRS D-10).
4. **No live CRM transport.** Requests are validated, dry-run previews work, failures are logged.
5. **External AI adapter unverified** until the `ai.*` package is merged.
6. **Docker image not built in this environment** (daemon unavailable). Compose configuration was
   validated with `docker compose config`.
7. **No CI workflow.** Adding one requires a decision on the target database service; the exact
   proposed workflow is in `docs/contributor-actions.md`.
8. **Frontend absent by design.** Integration guidance is in `docs/frontend-integration.md`.

---

## 11. Attribution and contribution workflow

This repository is the only source of truth. Individual repositories are review targets:

* `Infosys-Spring-Team-C/team_c_sai` - database/DevOps work, review in
  [`docs/database-review.md`](docs/database-review.md).
* `Infosys-Spring-Team-C/team-c-mahi` - AI/ML work, review in
  [`docs/ai-review.md`](docs/ai-review.md).

Sai and Mahidhar must submit their own pull requests so the work remains attributed to them.
This repository does not copy their code to bypass that process; it defines integration points and
documents the required changes in [`docs/contributor-actions.md`](docs/contributor-actions.md).

The backend implementation in this repository was authored by Mohamed Isharak M under his own Git
identity. It is not attributed to M Doran.

---

## 12. Documentation index

| Document | Contents |
|---|---|
| [`docs/SRS.md`](docs/SRS.md) | Authoritative requirements (FR/NFR, decisions) |
| [`docs/audit-report.md`](docs/audit-report.md) | Audit of all three repositories |
| [`docs/database-review.md`](docs/database-review.md) | File-specific review for Sai |
| [`docs/ai-review.md`](docs/ai-review.md) | File-specific review for Mahidhar |
| [`docs/api-contract.md`](docs/api-contract.md) | Routes, schemas, auth, errors |
| [`docs/frontend-integration.md`](docs/frontend-integration.md) | Checklist for Maheksaba |
| [`docs/test-report.md`](docs/test-report.md) | Exact commands and results |
| [`docs/git-report.md`](docs/git-report.md) | Branch, commits, push status |
| [`docs/pr-description.md`](docs/pr-description.md) | Ready-to-use pull request description |
| [`docs/contributor-actions.md`](docs/contributor-actions.md) | Actions for Sai and Mahidhar |
| [`docs/milestone-readiness.md`](docs/milestone-readiness.md) | What can be demonstrated |
