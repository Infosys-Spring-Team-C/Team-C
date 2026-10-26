# Database / DevOps Review - `team_c_sai`

**Reviewer:** Mohamed Isharak M
**Repository:** `https://github.com/Infosys-Spring-Team-C/team_c_sai`
**Commit reviewed:** `1ff01d9`
**Workspace reviewed:** `salesgenie-db-workspace/`
**Status:** review only. No files were modified in Sai's repository.

This review is written so Sai can act on it in her own fork and submit a pull request to Team-C.
It is not a request to copy her code; the canonical schema was independently derived from
`docs/SRS.md`.

---

## 1. What is genuinely good

1. **Eight-table decomposition matches the project plan.** `users`, `leads`, `lead_scores`,
   `company_insights`, `outreach_campaigns`, `sales_interactions`, `crm_sync_logs`,
   `sales_analytics` is the right set of entities.
2. **Referential integrity is taken seriously.** Every child table has an explicit
   `ON DELETE CASCADE` to `leads`.
3. **Index intent is sensible.** `ix_lead_scores_score_prob`, `ix_outreach_lead_status` and
   `ix_leads_lead_status` target realistic query patterns.
4. **PostgreSQL 16 Compose service is close to production-shaped.** Named volume, `pg_isready`
   health check, environment-driven credentials.
5. **Alembic tooling is present** (`migrations/env.py`, versioned revision), which is the correct
   direction even though the DDL is duplicated.

These ideas are reflected in the canonical migration. The specific DDL is not copied.

---

## 2. Schema findings

### D-01 (High) - The schema cannot support Modules 2-4

The SRS requires company analysis, configurable outreach and explainable scoring. The current
tables cannot store those outputs.

| Table | Missing capability | SRS reference |
|---|---|---|
| `leads` | `website`, `company_size`, `annual_revenue`, `funding_stage`, `tech_stack`, `company_description`, `prospect_role`, `engagement_history`, `explicit_needs`, `response_behavior`, `user_research`, `pain_points`, `lead_source` | FR-001..FR-015, Module 1/2 |
| `leads` | A single canonical lifecycle field. `lead_status` is a free `VARCHAR(50)` with values only in a comment; no validation. | FR-010, FR-011 |
| `company_insights` | Structured `business_needs`, `opportunities`, `pain_points`, `qualification`, `discovery_questions`, `missing_information`, `supporting_evidence`, `provider`, `model`. Currently three free-text columns. | FR-016..FR-025 |
| `outreach_campaigns` | `channel`, `tone`, `length`, `outreach_type`, `goal`, `industry_context`, `pain_points_used`, `provider`, `model`, `updated_at`. Only subject/content/status exist. | FR-026..FR-034 |
| `lead_scores` | `fit_score`, `intent_score`, `engagement_score`, `decision_readiness_score`, `factors` (JSON), `explanation`, `recommended_next_action`, `priority_level`, `model_version`. Only a float and a probability exist. | FR-035..FR-043 |
| `sales_interactions` | `transcript`, `key_points`, `action_items` as structured JSON, `follow_up_date`, `sentiment`. Currently `action_items` is free text. | FR-044..FR-048 |
| `crm_sync_logs` | `entity_type`, `operation`, `external_record_id`, `request_metadata`, `response_metadata`, `error_message`, `attempt_count`. | FR-049..FR-051 |

**Recommended fix.** Adopt the canonical column set in
`alembic/versions/0001_canonical_schema.py` (Team-C). If Sai wants to contribute the migration
itself, it should be rebased on that file rather than merged as a second competing revision.

---

### D-02 (High) - Default database password is committed

Evidence:

* `salesgenie-db-workspace/alembic.ini`: `sqlalchemy.url = postgresql+psycopg2://postgres:postgres_password@localhost:5432/salesgenie_db`
* `salesgenie-db-workspace/src/database/connection.py`: default fallback
  `postgresql+psycopg2://postgres:postgres_password@localhost:5432/salesgenie_db`
* `salesgenie-db-workspace/docker-compose.yml`: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres_password}`

A committed default credential is a security defect even in a student project, because it
normalises shipping databases with known passwords.

**Recommended fix.** Remove the fallback. Fail fast when `DATABASE_URL` is unset, and require
`POSTGRES_PASSWORD` with `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}`. Team-C's
`backend/config.py` and `docker-compose.yml` already do this.

---

### D-03 (Medium) - Two sources of DDL can drift

`init_schema.sql` and `migrations/versions/001_initial_eight_tables.py` both create the same
tables. Docker mounts the SQL file into `docker-entrypoint-initdb.d`, while Alembic applies the
Python revision. The two are not generated from each other, so a change in one silently diverges
from the other.

**Recommended fix.** Make Alembic the only source of truth. Delete `init_schema.sql` or replace it
with a documented "run `alembic upgrade head`" bootstrap. Team-C does the latter.

---

### D-04 (Medium) - `sales_analytics.user_id` is `NOT NULL`

`src/database/models/sales_analytics.py` and `init_schema.sql` require a user for every analytics
row. That prevents team-level, pipeline-level or global metrics, which the dashboard needs
(FR-052, FR-053). It also forces a fake "system" user for scheduled snapshots.

**Recommended fix.** Make the owner optional (`user_id NULL` = team-wide) or add a
`scope`/`team_id` column. Team-C omits the owner from `sales_analytics` and stores aggregate
snapshots.

---

### D-05 (Medium) - Audit history is destroyed with the lead

`crm_sync_logs.lead_id` is `NOT NULL ... ON DELETE CASCADE`. Deleting a lead erases the record of
what was sent to the CRM, which defeats the purpose of a sync log.

**Recommended fix.** `lead_id NULL ... ON DELETE SET NULL`, as in the canonical schema.

---

### D-06 (Medium) - No tests, no CI

There is no test directory and no workflow. Nothing verifies that:

* the SQL file and the Alembic revision agree;
* the ORM models match the migrated schema;
* constraints actually reject bad data.

**Recommended fix.** Add, at minimum:

* a migration test that runs `alembic upgrade head` then compares `inspect(engine)` with
  `Base.metadata`;
* a cascade/unique-constraint test;
* a GitHub Actions workflow with a `postgres:16` service container.

Team-C's `tests/test_schema.py` and `tests/test_postgres.py` are working examples.

---

### D-07 (Low) - Primary-key naming is inconsistent

Sai uses `lead_id`, `score_id`, `campaign_id`, `insight_id`, `interaction_id`, `sync_id`,
`analytics_id`, `user_id`. The canonical schema uses `id` everywhere, with `user_id` reserved for
the foreign key on `leads.owner_id`. Neither is wrong, but mixing `user_id` as both a PK and an FK
name across tables invites join mistakes.

**Recommended fix.** Pick one convention. Team-C uses `id` for primary keys.

---

### D-08 (Low) - `VARCHAR` lengths are inconsistent with the API contract

`leads.company_name` is `VARCHAR(150)` in SQL but `VARCHAR(240)` in the Pydantic/API layer in
Mahidhar's contract. `email` is `VARCHAR(255)` vs 320 in the API. A valid API request could fail at
the database layer.

**Recommended fix.** Align database lengths with the API contract, or add a database-level check
test. Canonical lengths: company 240, email 320, website 500.

---

### D-09 (Low) - Duplicate detection has no database support

`leads.email` is nullable and non-unique. Nothing prevents two leads with the same e-mail.

**Recommended fix.** Add a normalised, unique `email_key` column (nullable, so leads without an
e-mail are allowed). Team-C implements this and documents the policy: e-mail first, then
company + contact name.

---

## 3. DevOps findings

| # | Severity | File | Finding | Recommended fix |
|---|---|---|---|---|
| O-01 | High | `docker-compose.yml` | Default password fallback (see D-02) | Require the variable |
| O-02 | Medium | `docker-compose.yml` | Only the database is containerised; there is no API service, so the stack is not runnable end to end | Add an API service with `depends_on: condition: service_healthy` |
| O-03 | Medium | `docker-compose.yml` | Port `5432` is published on all interfaces by default (`"${POSTGRES_PORT:-5432}:5432"`) | Bind to `127.0.0.1` unless remote access is intended |
| O-04 | Medium | repository root | No CI workflow | Add the workflow described in D-06 |
| O-05 | Low | `migrations/env.py` | Database URL handling is split between `alembic.ini` and `connection.py`; no single override path | Read `DATABASE_URL` in `env.py`, as Team-C does |
| O-06 | Low | `docker-compose.yml` | `container_name` is fixed, which blocks scaling and collides with other local stacks | Remove `container_name` |
| O-07 | Low | `requirements.txt` | Dependencies are unpinned | Pin versions or use a lock file |

`init_schema.sql` mounted into `docker-entrypoint-initdb.d` only runs on an **empty** volume. If
Sai keeps it, the README must say that changing the SQL requires `docker compose down -v`.

---

## 4. Integration mapping - what Sai's PR should contain

The following is the recommended split between Sai's attributable contribution and the backend
work already done in Team-C.

### Accept through Sai's PR (her authorship)

1. **Migration discipline** - rebase her Alembic knowledge onto the canonical revision and add the
   first follow-up migration for any agreed change (for example, an analytics scope column).
2. **Index review** - verify the canonical indexes against real query plans and propose additions
   as a new revision.
3. **PostgreSQL Compose hardening** - health check, named volume, `127.0.0.1` port binding, no
   default password.
4. **CI workflow** - `postgres:16` service, `alembic upgrade head`, `pytest`, and a schema-parity
   check.
5. **Backup/restore and retention notes** - a short operational runbook (SRS section 13).

### Already implemented in Team-C (do not duplicate)

* Canonical eight-table models and migration.
* Environment-driven `DATABASE_URL` with no default credential.
* `email_key` uniqueness and duplicate policy.
* Cascade/SET NULL rules.
* SQLite + PostgreSQL schema tests.
* Non-root API Dockerfile and two-service Compose file.

### Do not merge as-is

* `init_schema.sql` alongside Alembic (D-03).
* `sales_analytics.user_id NOT NULL` (D-04).
* Any default password (D-02).
* The reduced column set (D-01) - it would regress Modules 2-4.

---

## 5. Definition of done for Sai's PR

- [ ] Branch created from current Team-C `main`.
- [ ] No secrets, no default passwords, no committed `.env`.
- [ ] `alembic upgrade head` succeeds on a clean PostgreSQL 16 database.
- [ ] `alembic downgrade base` succeeds.
- [ ] Schema-parity test passes.
- [ ] CI workflow runs green on the PR.
- [ ] README documents migration and rollback commands.
- [ ] PR description lists every file changed and why.
