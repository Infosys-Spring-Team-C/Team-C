# Milestone 3 DevOps & Database Engineering Completion Report

## SalesGenie AI — Module 5: CRM Integration & External Synchronization (data and deployment layer)

**Author / Role:** Marri Sai Surekha, Database / DevOps Engineer\
**Execution period in schedule:** October 31–November 10, 2026 (Days 20–30)\
**Target milestone and module:** Milestone 3 — Module 5 (CRM Integration & External Synchronization)\
**Report prepared:** 18 November 2026

---

## 1. Document header and executive summary

The Milestone 3 schedule gives the Database / DevOps Engineer one explicit row - Day 23, the
contact, activity and deal-stage sync work with `CRM_Sync_Logs`, shared with the Backend
Developer. The remaining database and deployment obligations are dependencies of the other
rows: the schema must carry the conversation and CRM tables, the migration must reproduce
that schema on PostgreSQL, and the Compose stack must still start the API against PostgreSQL.

The repository contains a canonical eight-table SQLAlchemy schema, a single Alembic migration
that reproduces it, a generated portable PostgreSQL DDL file, a generated ER diagram, a
database-only Compose file, and a full three-service Compose stack (`db`, `api`, `frontend`).
The Module 5 tables - `sales_interactions` and `crm_sync_logs` - are present in both the ORM
and the migration. No new migration was needed in Milestone 3: the schema already carried
them from the canonical baseline, and the work this milestone was to verify that the baseline
still matched the ORM, the migration and the deployed database.

Verified in this pass:

| Signal | Result |
|---|---|
| Canonical schema | **8 tables**, 110 columns, 6 foreign keys, 31 indexes |
| Generated DDL vs Alembic migration | **identical** (object by object; only `alembic_version` differs) |
| Schema and workspace tests | **13 passed** (`test_schema.py` 8, `test_db_workspace.py` 5) |
| PostgreSQL-only tests | **6**, run in the PostgreSQL 16 job |
| Full suite, PostgreSQL 16 (6 Nov 2026) | **177 passed, 0 skipped** (177-test suite at the time) |
| Full suite, SQLite (18 Nov 2026) | **191 passed, 7 skipped** (198 collected) |
| CI workflow | **Added** on 18 Nov 2026; not yet executed on GitHub |
| Compose stack (27 Oct 2026) | **3 services healthy**, API on PostgreSQL 16 |
| Clean install from declared dependencies (27 Oct 2026) | **37 frontend-adapter tests passed** |

Four limits are stated openly and are **not** presented as achievements:

1. **The Compose stack was not rebuilt on 18 November 2026.** The Docker daemon on the
   review host was unavailable (`npipe:////./pipe/dockerDesktopLinuxEngine`). The last
   verified build and start is 27 October 2026.
2. **PostgreSQL was not re-run on 18 November 2026.** The 177-passed result is from
   6 November 2026. The SQLite result is current.
3. **The CI workflow is new and has not run yet.** `.github/workflows/ci.yml` now runs the
   SQLite suite, the PostgreSQL 16 suite against a service container, the drift check and a
   credential scan. It has not been executed on GitHub, so no green run is claimed.
4. **The database layer is not production-operational.** There is no backup/restore
   procedure, no migration-per-change policy, no connection-pool tuning and no secret
   manager. The stack is a verified prototype deployment, not an operations runbook.

---

## 2. Milestone 3 deliverables and ownership matrix

| Day and date | SDLC phase | Scheduled task | Collaborating roles | Database / DevOps deliverable and evidence |
|---|---|---|---|---|
| Day 20 · Sat, Oct 31 | Buffer / Review | Close open Milestone 2 items; study CRM mapping; prepare transcripts | Backend + AI/ML | Not a database-owned row. Dependency checked: the canonical schema already declares `sales_interactions` and `crm_sync_logs`, so no schema change was raised. |
| Day 23 · Tue, Nov 3 | Development | Contact, activity and deal-stage sync with `CRM_Sync_Logs` | Backend + Database/DevOps | `crm_sync_logs` is defined in `backend/db.py` and created by `alembic/versions/0001_canonical_schema.py`; the table carries the provider, entity type, operation, external record id, status, request/response metadata, error message and attempt count, with indexes on `lead_id`, `status` and `(provider, status)`. |
| Day 26 · Fri, Nov 6 | Testing & QA | Finalise external endpoints; exercise the three workflows; prepare test notes | Backend + QA | Supporting evidence: PostgreSQL 16 job **177 passed, 0 skipped**; schema-parity check **identical** (110 columns, 6 FKs, 31 indexes). |
| Day 28 · Sun, Nov 8 | Buffer / Review | Prepare demo, fix CRM issues, draft the test report | QA + Backend | Deployment readiness re-checked from the 27 October Compose evidence. The stack was not rebuilt on 18 November (daemon unavailable). |
| Day 29 · Mon, Nov 9 | Milestone Evaluation | Demo CRM integration and call summaries | Full Team | No demo build, recording, minutes or evaluation result exists in the repository. This report does not claim a session occurred. |
| Day 30 · Tue, Nov 10 | Submission / Sign-off | Report submission and sign-off | Project Lead + QA | QA re-ran the suite, the UAT and the schema checks on 17-18 November; the sign-off row is still pending. |

The database-owned deliverable for this milestone is therefore the **schema and deployment
baseline that Module 5 runs on**, not a new set of tables. Claiming otherwise would overstate
the work.

**Attribution note.** The original database workspace (`salesgenie-db-workspace/`, commit
`d4f7fd7`) is this role's contribution. The canonical schema, the single migration, the
generated-artefact script and the added schema tests were authored and reconciled on the
shared repository by the Project Lead during integration. This report records the role's
deliverables and the verified state of the database layer; it does not claim sole authorship
of every file.

---

## 3. Technical architecture and core database implementations

### 3.1 One canonical schema, one migration

| Concern | Authoritative location |
|---|---|
| SQLAlchemy models | `backend/db.py` |
| Versioned migration | `alembic/versions/0001_canonical_schema.py` |
| Portable PostgreSQL DDL | `salesgenie-db-workspace/init_schema.sql` (generated) |
| ER diagram | `salesgenie-db-workspace/er_diagram.html` (generated) |
| Database-only Compose file | `salesgenie-db-workspace/docker-compose.yml` |
| Application Compose file | `docker-compose.yml` (repository root) |

The eight tables are `users`, `leads`, `company_insights`, `outreach_campaigns`,
`lead_scores`, `sales_interactions`, `crm_sync_logs` and `sales_analytics`. The schema keeps
unknown values honest: `lead_scores.conversion_probability` and the undefined dashboard
metrics are nullable rather than defaulted to a fabricated zero, and duplicate detection uses
a nullable unique `email_key` so blank e-mails do not collide.

### 3.2 The two Module 5 tables

**`sales_interactions`** stores the conversation record that the summariser writes and the
Conversations page reads:

| Column | Type | Constraint / purpose |
|---|---|---|
| `id` | Integer | Primary key |
| `lead_id` | Integer | Foreign key to `leads.id`, `ON DELETE CASCADE`, indexed |
| `interaction_type` | String(60) | `call` by default |
| `interaction_date` | DateTime with time zone | Indexed through the composite index below |
| `transcript` | Text | Raw notes or transcript |
| `summary` | Text | Stored summary |
| `key_points` | JSON | List, never invented by the database layer |
| `action_items` | JSON | List of explicit commitments |
| `follow_up_date` | DateTime with time zone, nullable | Optional |
| `sentiment` | String(40) | Defaults to empty, not guessed |

Composite index `ix_sales_interactions_lead_date` on `(lead_id, interaction_date)` supports
the per-lead history read.

**`crm_sync_logs`** is the audit table for every sync attempt:

| Column | Type | Constraint / purpose |
|---|---|---|
| `id` | Integer | Primary key |
| `lead_id` | Integer, nullable | Foreign key to `leads.id`, `ON DELETE SET NULL`, indexed |
| `provider` | String(40) | `salesforce` or `hubspot` at the API boundary |
| `entity_type` | String(80) | `contact`, `activity` or `deal` |
| `operation` | String(40) | `sync_contact`, `activity_log`, `update_stage` or `upsert` |
| `external_record_id` | String(240) | Empty for simulated attempts |
| `status` | String(32) | Indexed; `success`, `failed` or `pending` |
| `request_metadata` | JSON | Mapped provider-neutral payload |
| `response_metadata` | JSON | Simulator response and mode |
| `error_message` | Text | Failure detail, empty on success |
| `attempt_count` | Integer | Retry counter, starts at 1 |

Composite index `ix_crm_sync_provider_status` on `(provider, status)` supports the status
endpoint's recent-failure query. `ON DELETE SET NULL` deliberately preserves audit history
when a lead is deleted; a cascade here would destroy the evidence that a sync was attempted.

### 3.3 Migration and drift control

`alembic/versions/0001_canonical_schema.py` creates all eight tables, the six foreign keys
with their delete rules, and the 31 indexes, and it drops them in reverse order. The
generated DDL and the migration are compared object by object on a scratch database:
**110 columns, 6 foreign keys, 31 indexes on both sides**. The only object present in the
Alembic database and absent from the generated DDL is `alembic_version`, which is Alembic's
own bookkeeping table.

The workspace artefacts are **generated**, not hand-maintained:

```powershell
python scripts/render_db_workspace.py          # regenerate init_schema.sql and er_diagram.html
python scripts/render_db_workspace.py --check  # fail if the committed files are stale
```

`tests/test_db_workspace.py` runs the `--check` path inside the normal suite, so a schema
change cannot silently leave the workspace behind. This closes the "two sources of DDL can
drift" finding from the database review.

### 3.4 Deployment baseline

The application stack is three services:

| Service | Image / build | Health check | Notes |
|---|---|---|---|
| `db` | `postgres:16-alpine` | `pg_isready` | Named volume `salesgenie_pgdata` |
| `api` | `Dockerfile` (Python 3.11-slim, non-root user) | `/api/v1/health` | Runs `alembic upgrade head` before `uvicorn` |
| `frontend` | `frontend/Dockerfile` | `/_stcore/health` | Talks to the API only; receives no database credentials |

The API image installs the base requirements and optionally the AI extras
(`INSTALL_AI_EXTRAS=true`). It runs as an unprivileged `app` user and never needs root at
runtime. Migrations run once from the Compose command rather than from the image entrypoint,
so two API replicas cannot race the same migration.

The database-only Compose file in `salesgenie-db-workspace/` starts PostgreSQL 16 alone and
mounts `init_schema.sql` into `docker-entrypoint-initdb.d`. It exists so the portable
baseline can be exercised without the application. It intentionally has no default
`POSTGRES_PASSWORD`.

### 3.5 Reconciliation outcomes from the database review

The original database workspace shipped a second, independent eight-table schema. Both were
valid SQL, but only one could be true for the application. The canonical schema won, and the
workspace kept its role as the deployment baseline. The review findings that mattered:

| Finding | Outcome |
|---|---|
| Schema could not support Modules 2–4 (no auth columns, no structured intelligence, no score factors) | Canonical schema adopted; `password_hash`, `is_active`, JSON intelligence and explainable score factors are present |
| A default database password was committed | Both Compose files require `POSTGRES_PASSWORD` from the environment and fail closed |
| Two sources of DDL could drift | DDL and ER diagram are generated from the ORM; a drift test fails the suite |
| Audit history was destroyed with the lead | `crm_sync_logs.lead_id` uses `ON DELETE SET NULL` |
| Duplicate detection had no database support | Nullable unique `email_key` added; blank e-mails do not collide |
| No tests and no CI | Tests added (`test_schema.py`, `test_db_workspace.py`, `test_postgres.py`); a CI workflow was added on 18 November 2026 but has not run yet |

Full mapping, column by column: `docs/database-merge-notes.md`. Full review:
`docs/database-review.md`.

---

## 4. Database verification and schema controls

### 4.1 Test layers

| Layer | File | Tests | What it proves |
|---|---|---|---|
| Schema contract | `tests/test_schema.py` | 8 | Eight canonical tables, lifecycle and owner columns, migration up/down, migration matches ORM metadata, cascade delete, `email_key` uniqueness, blank e-mails do not collide, JSON round-trip |
| Workspace drift | `tests/test_db_workspace.py` | 5 | Generated artefacts match the ORM, DDL declares eight tables and six foreign keys with the agreed rules, honesty constraints are present, ER diagram covers every table |
| Real PostgreSQL | `tests/test_postgres.py` | 6 | Migration creates all tables, foreign keys use cascade and set-null, indexes exist, ORM round-trip and cascade, unique `email_key`, JSONB accepts structured values |

The PostgreSQL module refuses to run unless `TEST_DATABASE_URL` points at a database whose
name contains `test`, because the fixture drops and recreates the `public` schema.

### 4.2 Executed results

| Environment | Command | Result |
|---|---|---|
| SQLite (18 Nov 2026) | `python -m pytest -q` | **191 passed, 7 skipped** (198 collected) |
| PostgreSQL 16 (6 Nov 2026) | `python -m pytest -q` with `TEST_DATABASE_URL` | **177 passed, 0 skipped** in 83.29 s (177-test suite at the time) |
| Schema parity (26 Oct 2026) | scratch-database comparison | **identical** - 110 columns, 6 FKs, 31 indexes |
| Clean install (27 Oct 2026) | fresh virtual environment, `requirements-dev.txt` | **37 frontend-adapter tests passed** in 24.23 s |
| Compose stack (27 Oct 2026) | `docker compose build; docker compose up -d` | **3 services healthy**, API reports `database_dialect: postgresql` |

The 7 SQLite skips are 6 PostgreSQL-only tests and 1 opt-in LangGraph memory-checkpointer
test whose optional extra is not installed.

### 4.3 What the database evidence does not cover

* No run against a managed PostgreSQL service, a replica or a connection pooler.
* No migration test against an **existing** populated database: `0001` is the first and only
  migration, so an upgrade path from an earlier schema was never exercised.
* No backup, restore, failover or data-retention test.
* No row-level security; authorisation is enforced in the API, not in the database.
* No performance or index-usage measurement.

---

## 5. Integration testing, QA and demo readiness

| Item | State | Evidence |
|---|---|---|
| Canonical schema matches the API's ORM | Verified | `tests/test_schema.py`, full suite |
| Generated DDL matches the migration | Verified | `docs/qa/evidence/2026-10-26-schema-parity.txt` |
| PostgreSQL 16 migration and round-trip | Verified (6 Nov) | `docs/qa/evidence/2026-11-06-pytest-postgres.txt` |
| Compose stack starts and migrates PostgreSQL | Verified (27 Oct) | `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| Clean install from declared dependencies | Verified (27 Oct; 37 frontend-adapter tests) | `docs/qa/evidence/2026-10-27-clean-install.txt` |
| Module 5 tables present in ORM and migration | Verified | `backend/db.py`, `alembic/versions/0001_canonical_schema.py` |
| Compose rebuilt on 18 Nov | **Not run** | Docker daemon unavailable |
| CI pipeline | **Added, not yet run** | `.github/workflows/ci.yml` (SQLite, PostgreSQL 16, drift check, credential scan) |
| Live CRM transport | **Implemented, not verified against a real org** | `backend/services/crm_transport.py`; SRS D-06 still open |

The honest demo position is: the schema and the migration are verified on both dialects, and
the container topology was verified on 27 October 2026. A reviewer who asks for a live
rebuild on the day should be told that the daemon is unavailable on this host, not that the
stack was rebuilt.

---

## 6. Conclusion and transition to Milestone 4

The database and deployment layer is complete for a prototype milestone:

* one canonical eight-table schema, one migration, and generated DDL/ER artefacts that
  cannot drift silently;
* both Module 5 tables - `sales_interactions` and `crm_sync_logs` - defined, indexed and
  covered by tests;
* PostgreSQL 16 and SQLite both green on the canonical suite;
* a three-service Compose stack that was built, started and health-checked on 27 October
  2026.

The work that remains is operational hardening, not feature work: watching the first CI run
and fixing whatever it surfaces, a migration policy for schema changes after `0001`,
backup/restore and retention procedures, secret management instead of `.env`, and a rebuild of
the stack on a host with a working Docker daemon. Those items belong to the final-phase handoff
and are recorded as limitations here rather than presented as done.

---

**Evidence note:** This report is based on the repository state on 18 November 2026
(`main` at `825cc1c` plus these report files) and the captured artefacts under
`docs/qa/evidence/`. The PostgreSQL result is from 6 November 2026 and the Compose result
from 27 October 2026; neither was re-run on 18 November 2026 because the Docker daemon was
unavailable. The CI workflow was added but not executed. Scheduled tasks are not treated as
evidence of completion, and no live Salesforce or HubSpot call is claimed.
