# Milestone 3 - Database and DevOps Contribution

**Contributor:** Marri Sai Surekha, Database / DevOps Engineer\
**Module:** Milestone 3 - Module 5 (CRM Integration & External Synchronization), data and
deployment layer\
**Date:** 18 November 2026

---

## 1. Data layer scope in Module 5

Module 5 adds two capabilities to the product: summarising a sales conversation and
synchronising a lead with a CRM. Both need durable storage that the rest of the system can trust.

The conversation summary is content attached to a lead. The CRM synchronisation is an action
that can fail, be retried, and must be explainable after the fact. Those are different data
lifecycles, so they were given separate tables rather than one shared activity table.

The work covered by this document is:

* the two Module 5 tables and their ORM models;
* the single Alembic migration that creates the whole schema;
* the drift control that keeps models, migration and generated DDL identical;
* the generated DDL and ER diagram in `salesgenie-db-workspace/`;
* the three-service Compose baseline;
* the CI workflow that runs the suite, the drift check and a credential scan.

---

## 2. Canonical schema

### 2.1 Structure

| Signal | Result |
|---|---|
| Tables | 8 |
| Columns | 110 |
| Foreign keys | 6 |
| Indexes | 31 |

| Table | Purpose |
|---|---|
| `users` | Accounts and roles (`admin`, `manager`, `rep`, `viewer`) |
| `leads` | Canonical prospect record with lifecycle stage |
| `company_insights` | Stored intelligence output per lead |
| `outreach_campaigns` | Generated drafts and their status |
| `lead_scores` | Explainable score and factor breakdown |
| `sales_interactions` | Module 5 conversation summaries |
| `crm_sync_logs` | Module 5 CRM synchronisation audit |
| `sales_analytics` | Persisted analytics snapshots |

### 2.2 One migration as the source of truth

The schema is defined once, in SQLAlchemy models in `backend/db.py`. The Alembic migration
`alembic/versions/0001_canonical_schema.py` is generated from and compared against those models.
A single migration creates all eight tables, so a fresh database reaches the correct state in one
step.

The alternative - editing tables by hand and letting the migration drift - was rejected because
it makes a rebuild unpredictable. The drift check described in section 5 exists to enforce that
choice.

---

## 3. Conversation summary storage: `sales_interactions`

### 3.1 Structure

| Column | Type | Constraint / default |
|---|---|---|
| `id` | Integer | Primary key |
| `lead_id` | Integer | FK to `leads.id`, `ON DELETE CASCADE`, indexed |
| `interaction_type` | String(60) | `call` by default |
| `interaction_date` | DateTime with time zone | Defaults to the current UTC time |
| `transcript` | Text | Raw notes or transcript |
| `summary` | Text | Stored summary |
| `key_points` | JSON | List, empty by default |
| `action_items` | JSON | List, empty by default |
| `follow_up_date` | DateTime with time zone | Nullable |
| `sentiment` | String(40) | Empty by default |
| `created_at` / `updated_at` | DateTime | From the shared timestamp mixin |

### 3.2 Why the database stores rather than derives

The database holds what the summariser produced; it does not compute or infer it. `sentiment`
defaults to an empty string rather than a guessed label, and `key_points` and `action_items`
default to empty lists rather than placeholder text.

That choice is what makes the grounding tests meaningful: if the transcript contains no explicit
commitment, the stored `action_items` is empty. A database that filled in a default would make
fabrication indistinguishable from extraction.

### 3.3 Why the list fields are JSON

`key_points` and `action_items` are variable-length lists that are read with the interaction and
never queried independently. A child table would add two joins per read and a second write path
for no query benefit at this scale. JSON keeps the write atomic with the summary it belongs to.

### 3.4 Indexing and access pattern

`lead_id` is indexed on its own and again through the composite index
`ix_sales_interactions_lead_date (lead_id, interaction_date)`. The Conversations page reads the
summaries for one lead in reverse date order, which is exactly that index.

`ON DELETE CASCADE` is deliberate: an interaction is content owned by the lead, so removing the
lead removes its content.

---

## 4. CRM synchronisation audit: `crm_sync_logs`

### 4.1 Structure

| Column | Type | Constraint / default |
|---|---|---|
| `id` | Integer | Primary key |
| `lead_id` | Integer | FK to `leads.id`, `ON DELETE SET NULL`, indexed, nullable |
| `provider` | String(40) | `salesforce` or `hubspot` |
| `entity_type` | String(80) | `contact`, `activity` or `deal`; `lead` by default |
| `operation` | String(40) | `sync_contact`, `activity_log`, `update_stage`, `upsert` |
| `external_record_id` | String(240) | Provider record id, empty when absent |
| `status` | String(32) | `success`, `failed` or `pending`; indexed |
| `request_metadata` | JSON | Provider-neutral payload and mode |
| `response_metadata` | JSON | Response, mode and HTTP status |
| `error_message` | Text | Failure detail, empty on success |
| `attempt_count` | Integer | Starts at 1, incremented on retry |
| `created_at` / `updated_at` | DateTime | From the shared timestamp mixin |

### 4.2 Why `ON DELETE SET NULL` instead of `CASCADE`

A sync log is evidence that an action was attempted, not content owned by the lead. If a lead is
deleted, the product still needs to answer "was this ever sent, and did it fail?".

`ON DELETE SET NULL` keeps the row and detaches it from the deleted lead. `CASCADE` would erase
the audit trail exactly when an investigation is most likely.

### 4.3 Why the metadata columns exist

`request_metadata` stores the provider-neutral payload that was mapped for the CRM.
`response_metadata` stores the outcome, including the mode.

The mode is the important part: a simulated attempt records `mode: simulated` and a live attempt
records `mode: live`. Because the mode is in the database, a reviewer can separate the two
without trusting the UI or the API response.

Neither column ever receives a credential. Tokens stay in the request header and are never
written to the audit row.

### 4.4 Why the attempt counter lives in the row

Retry is a product rule: an attempt is recorded, then retried, then either succeeds or is left
failed. `attempt_count` makes that history readable in one row instead of requiring a second
table. A successful attempt cannot be retried again, which the API enforces and the tests cover.

### 4.5 Indexing for the status view

`status` is indexed on its own and together with `provider` through
`ix_crm_sync_provider_status (provider, status)`. The Conversations page shows a 24-hour sync
summary - total attempts, failures and failure rate - and the sync-log list filters by status.

---

## 5. Schema drift control

### 5.1 Generated artefacts

`scripts/render_db_workspace.py` renders two artefacts from the same ORM metadata:

| Artefact | Path |
|---|---|
| PostgreSQL DDL | `salesgenie-db-workspace/init_schema.sql` |
| ER diagram | `salesgenie-db-workspace/er_diagram.html` |

Neither is hand-maintained. The diagram cannot disagree with the schema because both come from
the models.

### 5.2 The check

`python scripts/render_db_workspace.py --check` regenerates the DDL and compares it to the
committed file and to the Alembic migration, object by object. It prints `OK` per artefact and
fails on any difference.

Current result: the generated DDL and the migration are identical, with only the
`alembic_version` bookkeeping table differing.

### 5.3 Test coverage

| Test file | Tests | What it covers |
|---|---|---|
| `tests/test_schema.py` | 8 | Tables, columns, foreign keys, indexes and constraint behaviour |
| `tests/test_db_workspace.py` | 5 | Generated DDL and ER diagram are current |
| `tests/test_postgres.py` | 6 | PostgreSQL-specific behaviour, run in the PostgreSQL 16 job |

---

## 6. Deployment baseline

### 6.1 Services

| Service | Image / build | Health check | Notes |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `pg_isready` | Named volume `salesgenie_pgdata` |
| `api` | `Dockerfile`, Python 3.11-slim, non-root user | `/api/v1/health` | Applies migrations before start-up |
| `frontend` | `frontend/Dockerfile` | `/_stcore/health` | Calls the API only |

### 6.2 Migration at start-up

The API container runs `alembic upgrade head` before `uvicorn`. A fresh volume therefore comes up
on the canonical schema with no manual step, and a redeploy applies any pending migration before
serving traffic.

### 6.3 Access boundary

The frontend container receives no database credentials. Its only path to data is the API, which
enforces JWT authentication and role checks. That keeps one authorisation boundary instead of
two, and means a UI bug cannot bypass RBAC.

### 6.4 CI workflow

`.github/workflows/ci.yml` defines three jobs:

| Job | What it runs |
|---|---|
| `sqlite` | Schema-drift check, then the full suite on SQLite |
| `postgres` | The full suite against a PostgreSQL 16 service container |
| `secrets` | A scan of tracked files for provider keys |

The workflow uses the same commands documented for local runs, so a green job means the same
checks a developer runs by hand.

---

## 7. Verification and proof

### 7.1 Executed results

| Check | Result | Date |
|---|---|---|
| Schema tests | **8 passed** | current |
| Workspace tests | **5 passed** | current |
| PostgreSQL-only tests | **6 passed** | current |
| Full suite, PostgreSQL 16 | **177 passed, 0 skipped** | 6 November 2026 |
| Full suite, SQLite | **191 passed, 7 skipped** (198 collected) | 18 November 2026 |
| Compose stack | **3 services healthy**, API migrated PostgreSQL 16 | 27 October 2026 |
| Clean install from declared dependencies | **37 passed** | 27 October 2026 |

The 7 SQLite skips are the 6 PostgreSQL-only tests plus one opt-in LangGraph test. They are
skips by design, not failures.

### 7.2 Reproduction commands

```powershell
# Schema and workspace checks
python -m pytest tests/test_schema.py tests/test_db_workspace.py -q

# Drift check: generated DDL and ER diagram match the models
python scripts/render_db_workspace.py --check

# Full suite on SQLite
$env:JWT_SECRET = "test-secret-value-0123456789"
python -m pytest -q

# Full suite on PostgreSQL 16
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q

# Stack
docker compose up --build -d
docker compose ps
```

### 7.3 Evidence files

| Artefact | Path |
|---|---|
| Schema parity | `docs/qa/evidence/2026-10-26-schema-parity.txt` |
| Compose verification | `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| PostgreSQL suite | `docs/qa/evidence/2026-11-06-pytest-postgres.txt` |
| SQLite suite | `docs/qa/evidence/2026-11-17-pytest-sqlite.txt` |
| Full role report | `docs/reports/Milestone 3 report - DevOps and Database.md` |
| CI workflow | `.github/workflows/ci.yml` |
| Generated workspace | `salesgenie-db-workspace/init_schema.sql`, `er_diagram.html` |

---

## 8. Milestone 3 deliverable checklist

| Deliverable | Implementation | Proof |
|---|---|---|
| `sales_interactions` table | `backend/db.py`, migration `0001` | `tests/test_schema.py` |
| `crm_sync_logs` table | `backend/db.py`, migration `0001` | `tests/test_schema.py`, `tests/test_api_ai.py` |
| Canonical migration | `alembic/versions/0001_canonical_schema.py` | Schema parity evidence |
| Generated DDL | `salesgenie-db-workspace/init_schema.sql` | `tests/test_db_workspace.py` |
| ER diagram | `salesgenie-db-workspace/er_diagram.html` | `tests/test_db_workspace.py` |
| Drift check | `scripts/render_db_workspace.py --check` | Drift check output |
| Compose baseline | `docker-compose.yml`, `Dockerfile`, `frontend/Dockerfile` | Compose verification evidence |
| CI workflow | `.github/workflows/ci.yml` | Workflow file |
| PostgreSQL verification | 6 dialect tests plus full suite | PostgreSQL suite evidence |
