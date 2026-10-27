# Defect Log

**Date:** 27 October 2026
**Author:** Mohamed Isharak M
**Application:** SalesGenie AI (Team C)
**Open defects:** 1 (0 Critical, 0 High, 0 Medium, 1 Low)
**Closed defects:** 14

**Severity** - Critical: cannot start / data loss Â· High: a Must requirement unmet or the
system states something untrue Â· Medium: a Should requirement unmet or a degraded
workflow Â· Low: cosmetic, documentation or no user-visible impact.
**Priority** - P1 before this milestone Â· P2 before final delivery Â· P3 when time allows.

---

## 1. Summary

| ID | Title | Severity | Priority | Status | Owner |
|---|---|---|---|---|---|
| BUG-001 | Application could not be imported at baseline (`No module named 'ai'`) | Critical | P1 | Fixed | Backend |
| BUG-002 | No `requirements.txt`, so the application could not be installed | Critical | P1 | Fixed | Backend |
| BUG-003 | Alembic "migration" was a `create_all()` stub | High | P1 | Fixed | Database |
| BUG-004 | Heuristic engine persisted a fabricated `conversion_probability` | High | P1 | Fixed | AI / Backend |
| BUG-005 | Analytics KPIs were stored as `0` rather than being undefined | High | P1 | Fixed | Backend |
| BUG-006 | Recommendation has no channel field (FR-032) | Medium | P2 | Closed (fixed) | Backend |
| BUG-007 | External AI adapter used the wrong request keys | High | P1 | Fixed | AI integration |
| BUG-008 | `ai.*` package absent from the integrated repository | High | P1 | Closed (package merged, gate 6/6) | AI (Mahidhar) / Lead |
| BUG-009 | Database owner's ER description contradicts her `init_schema.sql` | Medium | P2 | Closed (merge reconciliation) | Database (Sai) / Lead |
| BUG-010 | `VARCHAR(15)` phone column is too short | Low | P3 | Closed (merge reconciliation) | Database |
| BUG-011 | No `PATCH /api/v1/follow-ups/{id}` endpoint | Low | P3 | Open - accepted limitation | Backend |
| BUG-012 | Docker image and Compose stack never verified | High | P1 | Closed (fixed, stack verified) | DevOps / Lead |
| BUG-013 | `StarletteDeprecationWarning` from `TestClient` | Low | P3 | Closed (fixed) | Backend |
| BUG-014 | Frontend adapter mis-read the saved-analysis endpoint | High | P1 | Closed (fixed, 12/12) | Lead (frontend adapter) |
| BUG-015 | Frontend displayed a fabricated "Scoring Accuracy 98.4%" | High | P1 | Closed (fixed) | Lead (frontend) |

---

## 2. Open defects

### BUG-011 - No `PATCH /api/v1/follow-ups/{id}` endpoint

| Field | Value |
|---|---|
| Severity / Priority | Low / P3 |
| Status | Open - accepted limitation |
| Requirement | FR-052 (panel interaction) |
| Found by | Contract review |
| Owner | Backend |

**Description.** Follow-ups are derived on read from stored scores. There is no way to mark
one as done or dismissed, so the panel is read-only.

**Impact.** A user cannot clear a follow-up. Acceptable for the milestone; not for a
production workflow.

**Why it stays open.** `FR-052` requires a follow-up recommendations panel, which exists and
is populated from stored Module 4 output. Dismissing a follow-up is an interaction that the
SRS does not require. Implementing it needs a new persisted table (or a `dismissed_at`
column), which would change the eight-table schema, the migration, the generated ER diagram
and the schema tests. That is a deliberate scope decision, not an oversight, and it is
recorded here rather than silently closed.

**Suggested fix.** Persist a `follow_up_state` table keyed by lead, or add a `dismissed_at`
column to `lead_scores`.

---

## 3. Closed defects

### BUG-001 - Application could not be imported

| Field | Value |
|---|---|
| Severity | Critical |
| Status | Fixed in `9ddc617` |
| Found by | Baseline audit of `f3724a2` |

**Description.** `backend/api.py` imported `ai.providers` and `utils.*`, neither of which
existed in the repository. Every test module failed at collection.

```
tests/test_backend_api.py:6: in <module>
    from backend.api import app, get_db
backend/api.py:10: in <module>
    from ai.providers import create_provider
E   ModuleNotFoundError: No module named 'ai'
```

**Fix.** The application was rebuilt around `backend.intelligence`, which has a
`Protocol`-based contract, a deterministic offline engine and an adapter for the external
package. **Verified:** the suite collects and passes; `python -c "import main"` succeeds.

---

### BUG-002 - No `requirements.txt`

| Field | Value |
|---|---|
| Severity | Critical |
| Status | Fixed in `9ddc617` |
| Found by | Baseline audit |

**Description.** The repository had no dependency manifest, so a reviewer could not install
the application from a clean machine.

**Fix.** `requirements.txt` (runtime) and `requirements-dev.txt` (test tooling) were added.
**Verified:** a clean virtual environment built only from `requirements-dev.txt` runs the
full suite - `TC-DEP-003`.

---

### BUG-003 - Alembic migration was a `create_all()` stub

| Field | Value |
|---|---|
| Severity | High |
| Status | Fixed in `9ddc617` |
| Found by | Baseline audit |

**Description.** The single "migration" called `Base.metadata.create_all()` instead of
declaring operations. It could not be downgraded, and it would not track schema changes.

**Fix.** `alembic/versions/0001_canonical_schema.py` declares explicit `create_table` and
`drop_table` operations. **Verified:** upgrade and downgrade both succeed on PostgreSQL 16,
and migration output equals the ORM metadata (`test_migration_matches_orm_metadata`).

---

### BUG-004 - Fabricated `conversion_probability`

| Field | Value |
|---|---|
| Severity | High |
| Status | Fixed in `9ddc617` |
| Found by | AI integration review |

**Description.** The scoring path produced a number for `conversion_probability` from the
heuristic point total. A reader would interpret it as the output of a calibrated model. No
calibration exists (SRS D-13).

**Fix.** `conversion_probability` is `NULL` for the heuristic engine; `probability_band` and
`probability_note` explain that the band is uncalibrated. **Verified:**
`test_heuristic_never_returns_a_calibrated_probability`,
`test_scoring_is_explainable_and_never_fakes_probability`, UAT-14.

---

### BUG-005 - Analytics KPIs stored as `0`

| Field | Value |
|---|---|
| Severity | High |
| Status | Fixed in `9ddc617` |
| Found by | Integration review |

**Description.** `pipeline_value`, `average_response_time_days` and
`average_sales_cycle_days` were `NOT NULL DEFAULT 0`. A dashboard would have rendered `0`,
which reads as "no pipeline" rather than "not defined".

**Fix.** The three metrics return `value: null` with `pending_definition: true` and a
written definition field while SRS D-10 is open. `conversion_rate` is computed.
**Verified:** `test_analytics_returns_only_defensible_metrics`, UAT-18.

---

### BUG-006 - Recommendation has no channel field

| Field | Value |
|---|---|
| Severity / Priority | Medium / P2 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | FR-032, AC-019 |
| Found by | Live UAT (UAT-15) |
| Owner | Backend |

**Description.** FR-032 requires next-best-action recommendations to include *follow-up
timing, channel and content strategy*. `GET /api/v1/recommendations/{lead_id}` returned
`suggested_timing` and `follow_up_draft` but had no field identifying a channel (e-mail,
call, LinkedIn).

**Resolution.** `Recommendation.suggested_channel` is now part of the contract, typed as
`Literal["email", "phone", "linkedin", "meeting"] | None`. The deterministic engine sets
`email` for High and Medium priorities and `None` for Low, where no outreach is justified.
The external engine derives `email` only when the AI package actually produced a follow-up
draft and the priority is not Low, so the channel always matches content the user can send.
No channel is guessed.

**Verification.** `test_recommendation_priority_follows_evidence`,
`test_recommendation_endpoint` (asserts timing, channel and draft together) and
`test_external_recommendation_derives_a_channel_from_the_draft`. Full suite: **156 passed**
against PostgreSQL 16.15. Evidence:
`docs/qa/evidence/2026-10-27-pytest-postgres-open-defects.txt`.

---

### BUG-007 - External AI adapter used the wrong request keys

| Field | Value |
|---|---|
| Severity | High |
| Status | Fixed in `5be7308` |
| Found by | Adapter contract review |

**Description.** The adapter sent `outreach_type` and `goal`, while the AI package's
interface expects `channel` and `campaign_objective`. It also dropped `pain_points`,
`industry` and `user_research`, and forwarded `length`, which the package does not accept.
Against the real package this would have failed validation.

**Fix.** `_outreach_payload()` translates the keys, folds the extra context into
`company_insights`, and does not forward `length`. Package output is validated and any
failure is wrapped in `IntelligenceError`. **Verified:** `tests/test_external_adapter.py`
(10 tests) and `scripts/check_ai_integration.py` (6/6 against a stub).

---

### BUG-008 - The `ai.*` package was absent from the integrated repository

| Field | Value |
|---|---|
| Severity / Priority | High / P1 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | FR-011 to FR-018 (external engine) |
| Found by | Baseline audit and integration review |
| Owner | AI contributor (Mahidhar) / Lead |

**Description.** `backend/intelligence/external.py` targeted the AI module's documented
interface, but no `ai/` package existed in the integrated repository, so
`SALES_GENIE_AI_BACKEND=external` failed at engine construction.

**Resolution.** The contributor's package was applied from his submitted archive with him
as the git author (`feat(ai)` and `test(ai)` commits); the lead is the committer. Six
integration corrections followed in `fix(ai): integrate the package with the backend
contract` - the unsupported `grok_api_key` override, the Streamlit coupling in
`utils/config.py`, unclassified provider retries and the missing Gemini timeout, the
eight-factor/four-dimension mapping, dependency pins, and the optional LangGraph test guard.

**Verification.** `scripts/check_ai_integration.py` reports **6/6 operations passed** with
`SALES_GENIE_AI_BACKEND=external` and `SALES_GENIE_LLM_PROVIDER=mock`. Full suite: **131
passed, 6 skipped** (SQLite). Evidence:
`docs/qa/evidence/2026-10-27-ai-integration-gate.txt`.

**Residual risk.** Only the mock provider was exercised. Real OpenAI and Gemini calls
remain unverified because no key was used, and the package reports `used_mock: true`
accordingly.

---

### BUG-009 - ER description contradicts the SQL script

| Field | Value |
|---|---|
| Severity / Priority | Medium / P2 |
| Status | Closed in the database-merge reconciliation |
| Found by | Database review |
| Verified by | `tests/test_db_workspace.py`, `docs/qa/evidence/2026-10-26-schema-parity.txt` |

**Description.** The database contributor's written ER specification and her
`init_schema.sql` disagreed on several column sizes, on whether `users.email` was unique, on
the cascade rules and on the nullability of `conversion_probability`.

**Resolution.** Both artefacts are now **generated from one source** (`backend/db.py`) by
`scripts/render_db_workspace.py`. The contradiction cannot recur: `--check` fails on any
drift and `tests/test_db_workspace.py` runs that check in the suite. The generated DDL and the
Alembic migration were compared on a real PostgreSQL 16 instance and are identical across all
110 columns, 6 foreign keys and 31 indexes.

---

### BUG-010 - `VARCHAR(15)` phone column is too short

| Field | Value |
|---|---|
| Severity / Priority | Low / P3 |
| Status | Closed in the database-merge reconciliation |
| Found by | Database review |
| Verified by | `tests/test_db_workspace.py` |

**Description.** The proposed schema sized `phone` at 15 characters. International formats
with a country code, spaces and an extension exceed this, for example
`+44 20 7946 0958 ext 204`.

**Resolution.** The canonical schema uses `VARCHAR(80)`, and the generated DDL carries that
width. The value is asserted by the generated-SQL tests.

---

### BUG-012 - Docker image and Compose stack never verified

| Field | Value |
|---|---|
| Severity / Priority | High / P1 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | NFR-011, SRS D-14 |
| Found by | Test execution |
| Owner | DevOps / Project lead |

**Description.** `Dockerfile` and `docker-compose.yml` existed and were reviewed, but the
Docker daemon was not running on the test machine, so neither `docker build` nor
`docker compose up` was executed.

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

**Impact.** Deployment was unverified, and nothing in the repository claimed the container
image worked.

**Resolution.** Docker Desktop 29.7.2 was started. `docker compose build` built both images
(`team-c-api`, `team-c-frontend`), and `docker compose up -d` brought up `db`, `api` and
`frontend` with all three reporting `healthy`. The API applied the Alembic migration to
PostgreSQL 16 and `/api/v1/health` returned `status: ok`, `database: ok`,
`database_dialect: postgresql`, `auth_enabled: true`. The Streamlit container answered
`/_stcore/health` with `ok`.

**Additional hardening.** A `.dockerignore` was added. Without it, `COPY . .` would have
baked `.git/`, local databases and a developer's `.env` into the API image.

**Verification.** `scripts/check_frontend_integration.py` passed **12/12** against the
containerised API with authentication enabled, using a user created with
`backend.cli create-user`. The UI was then loaded in a browser: it reported
"Backend Active", computed a score and rendered the uncalibrated-probability notice.
Evidence: `docs/qa/evidence/2026-10-27-docker-compose-verification.txt`,
`docs/qa/evidence/2026-10-27-browser-ui-check.txt`.

---

### BUG-013 - `StarletteDeprecationWarning` from `TestClient`

| Field | Value |
|---|---|
| Severity / Priority | Low / P3 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | - |
| Found by | Test run warnings |
| Owner | Backend |

**Description.** `fastapi.testclient` emitted
`StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated;
install 'httpx2' instead.` The suite passed; the warning obscured real warnings.

**Resolution.** `httpx2==2.14.0` was added to `requirements-dev.txt`, which is what
Starlette's `TestClient` prefers. The 156-test PostgreSQL run now reports **1 warning**
(a JWT key-length warning from a test that deliberately uses a short key) and no Starlette
deprecation warning.

**Related cleanup.** `alembic.ini` gained `path_separator = os`, removing two Alembic
`DeprecationWarning`s about legacy `prepend_sys_path` / `version_locations` splitting.

---

### BUG-014 - Frontend adapter mis-read the saved-analysis endpoint

| Field | Value |
|---|---|
| Severity / Priority | High / P1 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | FR-020 to FR-025 (lead intelligence in the UI) |
| Found by | Headless Streamlit `AppTest` run during frontend integration |
| Owner | Lead (frontend adapter) |

**Description.** `frontend/api_compat.py` assumed `GET /api/v1/leads/{id}/insights`
returned one nested object (`{"research": ..., "qualification": ...}`). The canonical
endpoint returns a **list** of persisted analyses, newest first, with different key names
(`industry_context`, `business_needs`), and the `POST` variant returns a **flat**
`LeadIntelligence`. The adapter raised `AttributeError: 'list' object has no attribute 'get'`
and the intelligence page could not render.

**Why the first smoke run did not catch it.** The check only asserted that
`business_needs` was non-empty. The adapter's fallback text ("No explicit need is
recorded...") satisfied that, so a broken read looked like a pass. The check was tightened
to reject the placeholder and to require a qualification category, and a GET-saved check was
added.

**Resolution.** `normalise_insight` now accepts both the flat POST shape and the persisted
GET row shape; the GET branch selects the newest row and returns an honest 404 when no
analysis exists; the saved-outreach lookup now selects the newest draft instead of the
oldest.

**Verification.** `tests/test_frontend_compat.py`: **18 passed** (two shape tests, a
list/empty test, and the integrity test added with BUG-015). `scripts/check_frontend_integration.py`:
**12/12**. `AppTest`: **0 exceptions, 0 errors**. Evidence:
`docs/qa/evidence/2026-10-27-frontend-integration-gate.txt`,
`docs/qa/evidence/2026-10-27-frontend-apptest.txt`.

---

### BUG-015 - Frontend displayed a fabricated "Scoring Accuracy 98.4%"

| Field | Value |
|---|---|
| Severity / Priority | High / P1 |
| Status | Closed - fixed 27 October 2026 |
| Requirement | SRS D-10, D-13; project rule against fabricated model accuracy |
| Found by | Browser check of the containerised UI |
| Owner | Lead (frontend) |

**Description.** The hero header of `frontend/app.py` rendered a hard-coded card:
`Scoring Accuracy` / `98.4%`. No accuracy measurement exists, no calibration model is
configured, and the backend explicitly reports `conversion_probability: null`. The number
was presentation-only and would have been read as a measured model property.

**Resolution.** The card now reads the `ai_backend` value from `GET /health` and displays
`Scoring Engine` / `Heuristic` (or the configured engine name). It makes no accuracy or
calibration claim. A static regression test
(`test_frontend_does_not_claim_a_fabricated_accuracy`) fails if `98.4%` or
`Scoring Accuracy` returns to the source.

**Verification.** `AppTest`: **0 exceptions, 0 errors**; the rendered header contains
`Scoring Engine` and no `98.4`. Browser check of the rebuilt container shows the same.
Evidence: `docs/qa/evidence/2026-10-27-browser-ui-check.txt`.

---

## 4. Defect trend

| Status | Count |
|---|---|
| Closed | 14 |
| Open | 1 |
| **Total** | **15** |

All 15 defects are listed in section 1 with the stage that found them. No defect has been
reopened, and every closed defect has a verification reference in its entry.

The single open defect is BUG-011 (no way to dismiss a follow-up). It is a deliberate,
documented scope decision: `FR-052` requires the panel, which works, and adding persisted
dismissal state would change the eight-table schema and its generated artefacts.

