# Database Merge Notes - Sai Surekha's workspace

**Date:** 26 October 2026
**Prepared by:** Mohamed Isharak M (Project Lead)
**Contributor:** Marri Sai Surekha (Database DevOps Engineer)
**Contributor commit:** `d4f7fd7` "Add files via upload"
**Merge commit:** `fbe1fbc` (merge of `origin/team_c_sai`, `--no-ff`, not squashed)

---

## 1. What was merged

`origin/team_c_sai` added 22 files (1245 lines) under `salesgenie-db-workspace/`:

| Group | Files |
|---|---|
| PostgreSQL DDL | `init_schema.sql` |
| SQLAlchemy models | `src/database/models/` (8 models + `base.py` + `__init__.py`), `src/database/connection.py`, `src/database/__init__.py` |
| Alembic pipeline | `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/001_initial_eight_tables.py` |
| Docker baseline | `docker-compose.yml` |
| Documentation | `README.md`, `er_diagram.html` |
| Python deps | `requirements.txt` |
| Accidental binary | `salesgenie-db-workspace.lnk` (1.7 KB Windows shortcut) |

The merge was performed with `--no-ff` and **without squashing**, so `d4f7fd7` remains
authored and committed by `saisurekha914 <saisurekha914@gmail.com>`. Nothing was rewritten.

---

## 2. The conflict that had to be resolved

The repository already contained a canonical schema used by the API and the test suite:

* models - `backend/db.py`
* migration - `alembic/versions/0001_canonical_schema.py`

Sai's workspace described a **different** eight-table schema. Both were valid SQL; only one
could be true for the application. Keeping both would mean two sources of truth and a
guaranteed inconsistency.

### Decision

**The canonical schema wins.** Reasons:

1. It is the schema the API actually reads and writes; 122 tests and the live UAT run against it.
2. It carries the inputs Modules 2-4 require (lead context, outreach parameters, score factors).
3. It carries authentication state (`password_hash`, `is_active`) without which NFR-005 cannot be met.
4. It represents "unknown" honestly: `conversion_probability` and the open KPI metrics are nullable
   instead of `NOT NULL DEFAULT 0`.

Sai's workspace keeps its role as the **database deployment baseline**: portable DDL, a
database-only Compose file and the ER diagram, all generated from the canonical ORM.

---

## 3. Column-by-column reconciliation

### `users`

| Sai's design | Canonical | Reason |
|---|---|---|
| `user_id` PK | `id` PK | One `id` convention across all eight tables |
| `name VARCHAR(100)` | `full_name VARCHAR(200)` | Same purpose, wider |
| `email VARCHAR(255) UNIQUE` | `email VARCHAR(320)` unique index | RFC 5321 maximum |
| `role VARCHAR(50)` | `role VARCHAR(20)` | Constrained to `admin`/`manager`/`rep`/`viewer` in the API |
| `department VARCHAR(50)` | **removed** | No requirement reads it |
| `created_at` | `created_at`, `updated_at` | Audit pair |
| - | `password_hash VARCHAR(255)` | JWT/RBAC (NFR-005) |
| - | `is_active BOOLEAN` | Deactivation without deleting history |

### `leads`

| Sai's design | Canonical | Reason |
|---|---|---|
| `lead_id` PK | `id` PK | Convention |
| `company_name VARCHAR(150)` | `VARCHAR(240)` | Real company names exceed 150 |
| `industry VARCHAR(100)` | `VARCHAR(160)` | - |
| `contact_name VARCHAR(100)` | `VARCHAR(200)` | - |
| `email VARCHAR(255)` | `VARCHAR(320)` + `email_key` unique nullable | FR-008 duplicate detection; blank e-mails must not collide |
| `phone VARCHAR(50)` | `VARCHAR(80)` | **BUG-010** - international formats with extensions |
| `lead_status VARCHAR(50)` free text | `lifecycle_stage VARCHAR(32)` | FR-005/AC-004 need a closed vocabulary, not free text |
| `created_at` | `created_at`, `updated_at` | Audit pair |
| - | 14 context fields (`website`, `company_size`, `annual_revenue`, `funding_stage`, `tech_stack`, `company_description`, `prospect_role`, `engagement_history`, `explicit_needs`, `response_behavior`, `user_research`, `pain_points`, `lead_source`) | Module 2 analysis input (FR-011) and Module 4 scoring factors (FR-030) |
| - | `owner_id -> users.id ON DELETE SET NULL` | Ownership without losing the prospect when a user leaves |

### `company_insights`

| Sai's design | Canonical | Reason |
|---|---|---|
| `insight_id` PK | `id` PK | Convention |
| `business_needs TEXT` | `JSON` list | AC-006 requires structured, viewable output |
| `opportunities TEXT` | `JSON` list | Same |
| `industry_analysis TEXT` | `industry_context TEXT` + `pain_points JSON` | Separates analysis from identified challenges |
| `generated_at` | `created_at` | Naming consistency |
| - | `qualification JSON`, `discovery_questions JSON`, `missing_information JSON`, `supporting_evidence JSON` | FR-015, FR-018, and the non-fabrication rule |
| - | `recommended_value_proposition TEXT` | Module 2 output |
| - | `provider`, `model` | Traceability of which engine produced the row |

### `outreach_campaigns`

| Sai's design | Canonical | Reason |
|---|---|---|
| `campaign_id` PK | `id` PK | Convention |
| `email_subject VARCHAR(255)` | `subject VARCHAR(500)` | Subjects with personalisation run long |
| `email_content TEXT` | `body TEXT` | Channel-neutral (not e-mail only) |
| `campaign_status VARCHAR(50) DEFAULT 'Draft'` | `status VARCHAR(32) DEFAULT 'draft'` | Lower-case enum used by the API |
| `created_at` | `created_at`, `updated_at` | Audit pair |
| - | `channel`, `tone`, `length`, `outreach_type`, `goal`, `industry_context`, `pain_points_used` | The six SRS prompt inputs (FR-020) must be persisted to reproduce a draft |
| - | `provider`, `model` | Traceability |

### `lead_scores`

| Sai's design | Canonical | Reason |
|---|---|---|
| `score_id` PK | `id` PK | Convention |
| `lead_score FLOAT` | `score INTEGER` (0-100) | FR-028 defines an integer 0-100 scale |
| `conversion_probability FLOAT NOT NULL` | `FLOAT NULL` | **Honesty**: an uncalibrated heuristic must be able to store "not known" (D-09/D-13) |
| `generated_at` | `created_at` | Naming consistency |
| - | `fit_score`, `intent_score`, `engagement_score`, `decision_readiness_score` | The four required factors (FR-030) |
| - | `factors JSON`, `explanation TEXT`, `recommended_next_action TEXT` | Explainability (AC-017) |
| - | `priority_level`, `model_version` | Triage and traceability |

### `sales_interactions`

| Sai's design | Canonical | Reason |
|---|---|---|
| `interaction_id` PK | `id` PK | Convention |
| `interaction_type` | `interaction_type` | Kept |
| `summary TEXT` | `summary TEXT` | Kept |
| `action_items TEXT` | `action_items JSON` | FR-038 requires discrete items with evidence |
| `interaction_date` | `interaction_date` | Kept |
| - | `transcript TEXT` | FR-036 summarises supplied notes; the source must be retained |
| - | `key_points JSON`, `follow_up_date`, `sentiment` | FR-037 and follow-up scheduling |

### `crm_sync_logs`

| Sai's design | Canonical | Reason |
|---|---|---|
| `sync_id` PK | `id` PK | Convention |
| `lead_id NOT NULL ON DELETE CASCADE` | `lead_id NULL ON DELETE SET NULL` | An audit row must survive the record it describes (AC-024) |
| `crm_platform VARCHAR(50)` | `provider VARCHAR(40)` | Same purpose |
| `sync_status VARCHAR(50) DEFAULT 'Pending'` | `status VARCHAR(32) DEFAULT 'pending'` | API vocabulary |
| `timestamp` | `created_at`, `updated_at` | Reserved-word-free, consistent naming |
| - | `entity_type`, `operation`, `external_record_id`, `request_metadata`, `response_metadata`, `error_message`, `attempt_count` | FR-043 and retry support |

### `sales_analytics`

| Sai's design | Canonical | Reason |
|---|---|---|
| `analytics_id` PK | `id` PK | Convention |
| `user_id -> users.user_id NOT NULL` | **removed** | A snapshot is a team-wide aggregate, not a per-user row; the FK also made user deletion destructive |
| `conversion_rate NOT NULL DEFAULT 0` | `FLOAT NULL` | **Honesty**: D-10 has not defined the metric; `0` reads as "no conversions" |
| `pipeline_value NOT NULL DEFAULT 0` | `NUMERIC(15,2) NULL` | Same |
| `generated_at` | `metric_date`, `created_at` | Separates the measured period from the row timestamp |
| - | `total_leads`, `qualified_leads`, `converted_leads`, `average_lead_score` | Counts the dashboard actually renders |

---

## 4. What was removed from the workspace, and where it lives now

| Removed | Reason | Replacement |
|---|---|---|
| `salesgenie-db-workspace.lnk` | Accidental 1.7 KB Windows shortcut, not source | - |
| `src/database/models/*.py` (8 models) | Duplicate ORM with a conflicting schema | `backend/db.py` |
| `src/database/connection.py`, `src/database/__init__.py` | Duplicate engine/session setup | `backend/db.py`, `backend/config.py` |
| `alembic.ini`, `migrations/` | Second Alembic environment creating the conflicting schema | root `alembic/` (`0001_canonical_schema`) |
| `requirements.txt` | Duplicate dependency list using `psycopg2-binary` while the app uses `psycopg` 3 | root `requirements.txt` |
| `init_schema.sql` (original content) | Described the conflicting schema | regenerated from `backend/db.py` |
| `er_diagram.html` (original content) | Described the conflicting schema | regenerated from `backend/db.py` |

Everything removed is still recoverable from `d4f7fd7`:

```powershell
git show d4f7fd7:salesgenie-db-workspace/init_schema.sql
git show d4f7fd7:salesgenie-db-workspace/src/database/models/lead.py
```

The retained and corrected files are `README.md`, `init_schema.sql`, `er_diagram.html` and
`docker-compose.yml`.

---

## 5. What was kept from Sai's work

| Contribution | Where it survives |
|---|---|
| Eight-table architecture centred on the lead | Canonical schema |
| `ON DELETE CASCADE` for lead-owned child rows | Canonical schema (four tables) |
| Indexes for lead lookups, score ordering and campaign filtering | Canonical schema, extended |
| `lead_scores` and `outreach_campaigns` as the assigned tables, with composite indexes | Canonical schema, extended with the columns Modules 3-4 require |
| Dockerised PostgreSQL 16 baseline | `salesgenie-db-workspace/docker-compose.yml`, hardened (no default password) |
| ER diagram | `salesgenie-db-workspace/er_diagram.html`, regenerated |
| Database documentation | `salesgenie-db-workspace/README.md`, rewritten around the canonical schema |

The two tables she was assigned remain the two most detailed tables in the schema.

---

## 6. Drift protection added

| Artefact | Purpose |
|---|---|
| `scripts/render_db_workspace.py` | Generates `init_schema.sql` and `er_diagram.html` from `backend/db.py`; `--check` reports a diff |
| `tests/test_db_workspace.py` | Fails the suite if the generated files are stale, if a table or foreign key is missing, or if the nullable honesty columns become `NOT NULL` |

This means a future schema change cannot silently leave the workspace behind.

---

## 7. Defects closed by this reconciliation

| ID | Title | Resolution |
|---|---|---|
| BUG-009 | ER description contradicts `init_schema.sql` | Closed. The contradiction no longer exists: the ER diagram, the DDL and the ORM are all generated from one source, and a test enforces it. The historical discrepancy is documented in section 3. |
| BUG-010 | `VARCHAR(15)` phone column too short | Closed. The canonical schema uses `VARCHAR(80)`. |

---

## 8. Verification performed

```powershell
python scripts/render_db_workspace.py --check
python -m pytest -q
```

Results are recorded in [`qa/milestone-test-report.md`](qa/milestone-test-report.md) and
[`qa/evidence/`](qa/evidence/). The PostgreSQL run and the live UAT were repeated after the
merge; see the report for the exact counts.
