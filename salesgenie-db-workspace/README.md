# SalesGenie AI - Database Deployment Baseline

> **Infosys Virtual Internship 7.0**
> **Project:** SalesGenie AI - AI Sales Assistant & Lead Intelligence Platform
> **Original author:** Marri Sai Surekha (Database DevOps Engineer)
> **Reconciled by:** Mohamed Isharak M (Project Lead)

This folder is the **database deployment baseline** for the application: the portable
PostgreSQL DDL, a database-only Compose file and the entity-relationship diagram.

The SQLAlchemy models and the Alembic migration are **not** duplicated here. They live in
one place only:

| Concern | Authoritative location |
|---|---|
| SQLAlchemy models | [`backend/db.py`](../backend/db.py) |
| Versioned migration | [`alembic/versions/0001_canonical_schema.py`](../alembic/versions/0001_canonical_schema.py) |
| Portable PostgreSQL DDL | [`init_schema.sql`](init_schema.sql) (this folder, generated) |
| ER diagram | [`er_diagram.html`](er_diagram.html) (this folder, generated) |

`init_schema.sql` and `er_diagram.html` are **generated from `backend/db.py`** by
`scripts/render_db_workspace.py`. They cannot drift: `python scripts/render_db_workspace.py
--check` fails if either file is stale, and `tests/test_db_workspace.py` runs that check in
the normal test suite.

---

## 1. Why this folder no longer contains its own ORM and migration

The original submission shipped a second, independent schema: `user_id` / `lead_id` /
`score_id` primary keys, a `lead_status` free-text column, an Alembic environment of its own
and a `src/database/` package. It was internally consistent but **incompatible with the
application**: the backend needs credential columns for JWT/RBAC, the Module 2 inputs on the
lead, structured intelligence, the six outreach parameters, explainable score factors, the
conversation transcript and a durable CRM audit log.

Shipping two schemas in one repository guarantees that one of them is wrong. The application
schema in `backend/db.py` is the one the 117-test suite and the API actually use, so it is
the source of truth. The duplicate ORM, the second Alembic environment and the Windows
shortcut were removed in a follow-up commit; every removed file remains in git history at
commit `d4f7fd7`.

The full mapping from the original design to the canonical schema, including what was kept,
widened, made nullable and added, is in
[`docs/database-merge-notes.md`](../docs/database-merge-notes.md).

---

## 2. The eight tables

| # | Table | Purpose | Foreign keys |
|---|---|---|---|
| 1 | `users` | Authentication principals and RBAC roles | - |
| 2 | `leads` | Prospect master record (Module 1 inputs for Modules 2-6) | `owner_id -> users.id` (`SET NULL`) |
| 3 | `company_insights` | Stored Module 2 intelligence | `lead_id -> leads.id` (`CASCADE`) |
| 4 | `outreach_campaigns` | Generated and edited outreach (Module 3) | `lead_id -> leads.id` (`CASCADE`) |
| 5 | `lead_scores` | Append-only score history (Module 4) | `lead_id -> leads.id` (`CASCADE`) |
| 6 | `sales_interactions` | Conversation summaries and notes (Module 5) | `lead_id -> leads.id` (`CASCADE`) |
| 7 | `crm_sync_logs` | CRM synchronisation audit trail (Module 5) | `lead_id -> leads.id` (`SET NULL`) |
| 8 | `sales_analytics` | Point-in-time KPI snapshots (Module 6) | - |

Six foreign keys in total. `sales_analytics` is deliberately not tied to a lead: a snapshot
is a team-wide aggregate, not a per-prospect row.

### Delete policy

| Relationship | Rule | Why |
|---|---|---|
| Lead removed | Insights, campaigns, scores and interactions are deleted | They have no meaning without the lead |
| Lead removed | CRM sync log survives with `lead_id = NULL` | An audit trail must outlive the record it describes |
| User removed | Owned leads survive with `owner_id = NULL` | A prospect is company property, not personal property |

### Uniqueness

| Constraint | Purpose |
|---|---|
| `users.email` unique | One account per address |
| `leads.email_key` unique, nullable | Duplicate detection (FR-008). Blank e-mails are stored as `NULL`, so prospects without an address never collide |

---

## 3. Using the baseline

### 3.1 Database only (Docker)

```powershell
cd salesgenie-db-workspace
$env:POSTGRES_PASSWORD = "<choose a local password>"
docker compose up -d
```

PostgreSQL 16 starts on `127.0.0.1:5432` and executes `init_schema.sql` on first startup.
The password has no default: Compose refuses to start without `POSTGRES_PASSWORD`.

To inspect:

```powershell
docker compose exec db psql -U salesgenie -d salesgenie -c "\dt"
docker compose down          # keeps the volume
docker compose down -v       # destroys the volume and the data
```

### 3.2 The whole application

Use the root [`docker-compose.yml`](../docker-compose.yml) instead. It starts PostgreSQL and
the API, and applies the schema with `alembic upgrade head`, which is the same schema this
folder renders.

### 3.3 Against an existing database

```powershell
python -m alembic upgrade head      # from the repository root
```

`init_schema.sql` is for a **brand-new** database (the Docker entrypoint). It uses
`CREATE TABLE IF NOT EXISTS` and is not a migration; do not run it over a database that
Alembic already manages.

---

## 4. Verifying that the baseline is current

```powershell
# 1. The generated artefacts still match backend/db.py
python scripts/render_db_workspace.py --check

# 2. The automated check inside the test suite
python -m pytest tests/test_db_workspace.py -q

# 3. The schema itself, on a real PostgreSQL instance
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q
```

If a model changes and the artefacts are not regenerated, step 1 and step 2 fail with a
diff. Regenerate with:

```powershell
python scripts/render_db_workspace.py
```

---

## 5. ER diagram

Open [`er_diagram.html`](er_diagram.html) in a browser. It renders with Mermaid from a CDN,
so it needs network access the first time. The diagram is generated from the same metadata
as the DDL and lists every column with its `PK` / `UK` / `FK` marker plus the delete rule on
each relationship.

---

## 6. Status

| Item | Status |
|---|---|
| Eight tables, six foreign keys | Implemented and tested (`tests/test_schema.py`, `tests/test_postgres.py`) |
| Migration up and down on PostgreSQL 16 | Verified |
| DDL and ER diagram match the ORM | Enforced by `tests/test_db_workspace.py` |
| Docker execution of this Compose file | **Not verified** - no Docker daemon was available on the test machine (BUG-012) |

Nothing in this folder claims that the Compose stack has been started. The SQL is verified
against a real PostgreSQL 16 instance through the migration and test suite; the container
wiring is reviewed but unexecuted.
