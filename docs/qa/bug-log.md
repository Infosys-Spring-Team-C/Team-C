# Defect Log

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Application:** SalesGenie AI (Team C)
**Open defects:** 4 (0 Critical, 1 High, 1 Medium, 2 Low)
**Closed defects:** 9

**Severity** - Critical: cannot start / data loss · High: a Must requirement unmet or the
system states something untrue · Medium: a Should requirement unmet or a degraded
workflow · Low: cosmetic, documentation or no user-visible impact.
**Priority** - P1 before this milestone · P2 before final delivery · P3 when time allows.

---

## 1. Summary

| ID | Title | Severity | Priority | Status | Owner |
|---|---|---|---|---|---|
| BUG-001 | Application could not be imported at baseline (`No module named 'ai'`) | Critical | P1 | Fixed | Backend |
| BUG-002 | No `requirements.txt`, so the application could not be installed | Critical | P1 | Fixed | Backend |
| BUG-003 | Alembic "migration" was a `create_all()` stub | High | P1 | Fixed | Database |
| BUG-004 | Heuristic engine persisted a fabricated `conversion_probability` | High | P1 | Fixed | AI / Backend |
| BUG-005 | Analytics KPIs were stored as `0` rather than being undefined | High | P1 | Fixed | Backend |
| BUG-006 | Recommendation has no channel field (FR-032) | Medium | P2 | Open | Backend |
| BUG-007 | External AI adapter used the wrong request keys | High | P1 | Fixed | AI integration |
| BUG-008 | `ai.*` package absent from the integrated repository | High | P1 | Closed (package merged, gate 6/6) | AI (Mahidhar) / Lead |
| BUG-009 | Database owner's ER description contradicts her `init_schema.sql` | Medium | P2 | Closed (merge reconciliation) | Database (Sai) / Lead |
| BUG-010 | `VARCHAR(15)` phone column is too short | Low | P3 | Closed (merge reconciliation) | Database |
| BUG-011 | No `PATCH /api/v1/follow-ups/{id}` endpoint | Low | P3 | Open | Backend |
| BUG-012 | Docker image and Compose stack never verified | High | P1 | Open | DevOps / Lead |
| BUG-013 | `StarletteDeprecationWarning` from `TestClient` | Low | P3 | Open | Backend |

---

## 2. Open defects

### BUG-006 - Recommendation has no channel field

| Field | Value |
|---|---|
| Severity / Priority | Medium / P2 |
| Status | Open |
| Requirement | FR-032, AC-019 |
| Found by | Live UAT (UAT-15) |
| Owner | Backend |

**Description.** FR-032 requires next-best-action recommendations to include *follow-up
timing, channel and content strategy*. `GET /api/v1/recommendations/{lead_id}` returns
`suggested_timing` and `follow_up_draft` but has no field identifying a channel (e-mail,
call, LinkedIn).

**Reproduction.**

```powershell
$t = (Invoke-RestMethod -Method Post -Uri "$b/api/v1/auth/token" `
      -Body @{username=$e; password=$p}).access_token
Invoke-RestMethod -Uri "$b/api/v1/recommendations/$leadId" `
  -Headers @{Authorization="Bearer $t"} | ConvertTo-Json -Depth 5
```

**Expected.** A field naming the recommended channel.
**Actual.** No channel key; the JSON contains `recommended_action`, `reason`,
`supporting_evidence`, `priority`, `suggested_timing`, `follow_up_draft`, `status`.

**Impact.** The dashboard can show *when* and *what* but not *through which channel*.
`AC-019` cannot be marked PASS.

**Suggested fix.** Add `suggested_channel: Literal["email", "phone", "linkedin", "meeting"]`
to the `Recommendation` contract and populate it in both engines; extend the contract test.

---

### BUG-011 - No `PATCH /api/v1/follow-ups/{id}` endpoint

| Field | Value |
|---|---|
| Severity / Priority | Low / P3 |
| Status | Open - deferred |
| Requirement | FR-052 (panel interaction) |
| Found by | Contract review |
| Owner | Backend |

**Description.** Follow-ups are derived on read from stored scores. There is no way to mark
one as done or dismissed, so the panel is read-only.

**Impact.** A user cannot clear a follow-up. Acceptable for the milestone; not for a
production workflow.

**Suggested fix.** Persist a `follow_up_state` table keyed by lead, or add a `dismissed_at`
column to `lead_scores`.

---

### BUG-012 - Docker image and Compose stack never verified

| Field | Value |
|---|---|
| Severity / Priority | High / P1 |
| Status | Open - environment blocker |
| Requirement | NFR-011, SRS D-14 |
| Found by | Test execution |
| Owner | DevOps / Project lead |

**Description.** `Dockerfile` and `docker-compose.yml` exist and are reviewed, but the
Docker daemon was not running on the test machine, so neither `docker build` nor
`docker compose up` was executed.

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

**Impact.** Deployment is **unverified**. Nothing in this repository claims the container
image works.

**Resolution.** Start Docker, run `docker compose up --build -d`, confirm
`/api/v1/health` returns `status: ok`, then close this defect with the output attached.

---

### BUG-013 - `StarletteDeprecationWarning` from `TestClient`

| Field | Value |
|---|---|
| Severity / Priority | Low / P3 |
| Status | Open - accepted |
| Requirement | - |
| Found by | Test run warnings |
| Owner | Backend |

**Description.** `fastapi.testclient` emits
`StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated;
install 'httpx2' instead.` The suite passes; the warning is noise.

**Impact.** None on behaviour. It obscures real warnings in the output.

**Suggested fix.** Move the test client to the supported transport when the dependency set
is next updated.

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

## 4. Defect trend

| Stage | Found | Closed | Open |
|---|---|---|---|
| Baseline audit (`f3724a2`) | 3 | 3 | 0 |
| Integration review | 2 | 2 | 0 |
| Adapter review | 1 | 1 | 0 |
| Live UAT and environment checks | 4 | 0 | 4 |
| Database review | 2 | 2 | 0 |
| Test-tooling review | 1 | 0 | 1 |
| **Total** | **13** | **8** | **5** |

No defect has been reopened. Every closed defect has a verification reference in the row
above.
