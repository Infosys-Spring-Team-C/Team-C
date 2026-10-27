# Integration Test Plan and Results

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Scope:** how the layers of SalesGenie AI behave when connected

A unit test proves a function works. An integration test proves the system works. This
document records what was connected, how it was exercised, and what actually happened.

---

## 1. Integration points

| ID | Connection | Direction | Mechanism | Status |
|---|---|---|---|---|
| INT-A | FastAPI → PostgreSQL | API calls SQLAlchemy | Session dependency, one session per request | Verified |
| INT-B | FastAPI → SQLite | API calls SQLAlchemy | Same code path, file database | Verified |
| INT-C | FastAPI → heuristic AI engine | In-process call | `backend.intelligence.get_engine()` | Verified |
| INT-D | FastAPI → external AI package | In-process adapter | `ExternalAIEngine`, package `ai.*` | Verified against a stub only - **BUG-008** |
| INT-E | FastAPI → Streamlit frontend | HTTP + JSON | Documented contract | Verified - 12/12 gate with auth enabled, plus a browser check |
| INT-F | API container → PostgreSQL container | TCP | Docker Compose | Verified - db, api and frontend healthy; migration applied |
| INT-G | API → CRM provider | HTTPS | Not configured | **Blocked** - SRS D-06 |
| INT-H | API → e-mail provider | SMTP/API | Not configured | **Blocked** - SRS D-05 |

---

## 2. INT-A / INT-B - API and database

**Method:** the full pytest suite runs every endpoint against a real database, not a mock.
`tests/test_postgres.py` repeats the critical paths on PostgreSQL 16.

**What is proven**

* A record created through `POST /leads` is readable through `GET /leads/{id}` in a later
  request and a different session.
* Deleting a lead removes its insights, campaigns, scores and interactions, and leaves the
  CRM audit log with a nulled `lead_id`.
* A unique e-mail violation surfaces as `409` from the API, not as a `500`.
* A failed transaction does not leave a partial record.

**Result:** PASS on both dialects.

---

## 3. INT-C - API and the default AI engine

**Method:** `SALES_GENIE_AI_BACKEND=heuristic` (the default). Every AI endpoint is called
through the API, and the persisted row is read back.

**What is proven**

* `POST /leads/{id}/insights` produces structured analysis, persists it, and
  `GET /leads/{id}/insights` returns it.
* `POST /outreach/generate` returns a draft **and** a campaign row; the campaign is
  retrievable by id and in the lead's history.
* `POST /leads/{id}/scores` persists a score whose factor points sum to the reported score.
* `POST /conversations/summarize` persists the interaction with its summary, key points and
  action items.
* The same stored lead feeds Modules 2, 3, 4, 5 and 6 - no module invents its own copy of
  the prospect.

**Result:** PASS. Live UAT confirms all of it over real HTTP (UAT-11, UAT-12, UAT-14,
UAT-16, UAT-18).

---

## 4. INT-D - API and the external AI package

**Method:** `SALES_GENIE_AI_BACKEND=external` with a stub package installed that exposes
the interface the AI module is documented to provide. `tests/test_external_adapter.py`
contains 10 tests against that stub. `scripts/check_ai_integration.py` performs the same
six operations and prints a pass/fail line per operation.

**What is proven**

* The adapter constructs from the documented interface and fails loudly when the package is
  absent.
* Request translation is correct: `outreach_type` maps to the package's `channel`, `goal`
  maps to `campaign_objective`, and `pain_points`, `industry` and `user_research` are folded
  into `company_insights`. `length` has no equivalent in the package and is not forwarded.
* Package exceptions become `IntelligenceError`, which the API turns into `502 ai_failed`.
* Malformed package output is rejected before it reaches the database.

**What is NOT proven:** that the real `ai.*` package behaves as its documented interface
says. The package is not present in the integrated repository. This is **BUG-008** and it
is owned by the AI contributor.

**Result:** PASS against the stub, BLOCKED against the real package.

---

## 5. INT-E - API and the frontend contract

**Method:** the contract is frozen in [`../api-contract.md`](../api-contract.md) and
asserted by the API tests: response shapes, pagination headers, error envelope, the
`id`-as-string convention and the `null` + `pending_definition` KPI shape.

**What is proven**

* Every field the frontend needs is present in a documented response.
* List endpoints return a bare array with pagination headers, so the frontend can show
  counts without a second call.
* The AI endpoints are server-side. The frontend must call generation endpoints and must
  not post client-computed AI output.
* `501` responses carry a machine-readable `code` so the UI can disable the button and
  explain why.

**What is NOT proven:** that the Streamlit application consumes the contract correctly.
No frontend exists yet. This is `TC-E2E-003`.

**Result:** contract verified, consumption BLOCKED.

---

## 6. INT-F - Container topology

**Method:** `docker compose build` followed by `docker compose up -d`, then the health
endpoints and the frontend compatibility gate.

**Result:** PASS. Docker 29.7.2 built both images. `db`, `api` and `frontend` all became
healthy; the API applied the Alembic migration to PostgreSQL and returned `status: ok`,
`database: ok`, `database_dialect: postgresql`, `auth_enabled: true`; the Streamlit
container answered `/_stcore/health` with `ok`. The live gate passed 12/12 with a real
login. Evidence:
[`evidence/2026-10-27-docker-compose-verification.txt`](evidence/2026-10-27-docker-compose-verification.txt).
BUG-012 is closed.

---

## 7. INT-G / INT-H - External services

Both are refused visibly and safely:

* `POST /outreach/send` → `501 email_transport_not_configured`, nothing sent, campaign
  unchanged.
* `POST /crm/sync` → `501 crm_not_configured`, a failure row written to `crm_sync_logs`,
  local records intact.

**Result:** PASS as specified. A silent success here would have been a defect.

---

## 8. Cross-module integration scenarios

| ID | Scenario | Steps | Result |
|---|---|---|---|
| INT-S-01 | Prospect → intelligence → outreach → score → recommendation | Create a lead, analyse it, generate outreach, score it, request the recommendation. All five steps use the same stored lead. | PASS (UAT-05, 11, 12, 14, 15) |
| INT-S-02 | Prospect → conversation → follow-up | Create a lead, summarise a call, score it, read the follow-up list. | PASS (UAT-05, 16, 14, 19) |
| INT-S-03 | Prospect → CRM failure → local integrity | Attempt a CRM sync, confirm `501`, confirm the sync log grew and the lead still exists. | PASS (UAT-17) |
| INT-S-04 | Prospect → delete → analytics | Delete a lead and confirm the dashboard counts and follow-up list recompute. | PASS (UAT-21 then UAT-18 ran before deletion; counts recompute on read) |
| INT-S-05 | Import → list → filter | Import a CSV, list with search and pagination, confirm totals. | PASS (UAT-09, UAT-07) |
| INT-S-06 | Auth → RBAC → business call | Log in as a viewer, attempt a write, confirm `403`; confirm read still works. | PASS (UAT-20) |

---

## 9. Live integration run

`scripts/qa_uat.py` starts from a freshly migrated PostgreSQL database, creates its own
data over HTTP and asserts each step. Result:

| Metric | Value |
|---|---|
| Workflows executed | 21 |
| Passed | 20 |
| Partial | 1 (FR-032 channel, BUG-006 - fixed after this run) |
| Failed | 0 |

Evidence: [`evidence/2026-10-26-uat-live-postgres-heuristic.md`](evidence/2026-10-26-uat-live-postgres-heuristic.md).

---

## 10. Integration risks carried forward

| Risk | Mitigation |
|---|---|
| The external AI package may not match its documented interface | Adapter tests pin the translation; `check_ai_integration.py` gives a 6-operation gate before any merge |
| The frontend may assume a different response shape | Contract is written and frozen; the contract tests fail if a shape changes |
| Container startup may fail on first real use | Recorded as an open defect; must be executed before the final milestone |
| Schema merge may break the API | Database tests assert ORM **and** migration output, so drift fails immediately |
