# Test Plan

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Prepared by:** Mohamed Isharak M - QA / Test Engineer and Project Lead
**Version:** 1.0
**Date:** 26 October 2026
**Status:** Approved for Milestone evaluation

---

## 1. Purpose

This plan defines how Team C verifies that the integrated SalesGenie AI application
works, meets the requirements recorded in [`../SRS.md`](../SRS.md), and is ready to be
demonstrated at a milestone review.

It covers the whole system, not only the QA engineer's own code: the database layer
(Module 1), prospect management (Module 2), lead intelligence (Module 3), outreach
(Module 4), scoring and recommendations (Module 5), conversations and CRM (Module 6),
analytics, the API layer, and the integration points between them.

---

## 2. Scope

### 2.1 In scope

| Area | What is verified |
|---|---|
| Prospect management | Create, read, list, search, paginate, update, delete, lifecycle stages, duplicate detection, CSV import |
| Lead intelligence | Company analysis, business needs, opportunities, industry context, qualification, persistence, invalid-output rejection |
| Outreach | Generation with the six SRS inputs, editing, history, campaign storage, honest handling of the send action |
| Scoring and recommendations | 0-100 explainable score, four SRS factors, append-only history, degraded behaviour on missing data, next-best-action |
| Conversations | Note/transcript summarisation, key points, action items, storage, no fabrication |
| CRM | Field-mapping validation, sync pre-flight, failure logging, local-record preservation |
| Analytics | Conversion rate, KPI honesty, pipeline distribution, follow-up derivation, empty-dataset behaviour |
| API | Contract, status codes, error envelope, pagination headers, OpenAPI document |
| Security | JWT issuance and validation, password hashing, role-based access control, secret hygiene |
| Database | Schema, keys, constraints, cascade behaviour, migrations up and down, JSON columns, dialect parity |
| Integration | API↔database, API↔AI engine, API↔Streamlit contract, container topology |

### 2.2 Out of scope for this milestone

| Excluded | Reason |
|---|---|
| Streamlit user interface | Not yet delivered by the frontend owner; backend contract is frozen and documented in [`../api-contract.md`](../api-contract.md) instead |
| Real e-mail delivery | Provider unconfirmed (SRS D-05). Verified that the API refuses the action visibly |
| Live Salesforce/HubSpot synchronisation | Credentials and sandbox unconfirmed (SRS D-06) |
| Scoring accuracy against a labelled dataset | Metric and dataset undefined (SRS D-13) |
| Performance benchmarking against the 5-second target | Measurement conditions undefined (SRS D-11) |
| Penetration testing | Not requested for this milestone |

---

## 3. Test levels and ownership

| Level | Question answered | Technique | Owner |
|---|---|---|---|
| Unit | Does one function or rule behave correctly in isolation? | `pytest` against services, validators, security helpers and the heuristic engine | QA engineer (authored across all modules) |
| API | Does each endpoint honour its contract? | `pytest` with `TestClient`, plus a live-server run | QA engineer |
| Database | Is data stored, constrained and migrated correctly? | `pytest` against SQLite and PostgreSQL 16, Alembic up/down | QA engineer with the database owner |
| Integration | Do the layers work together? | Live Uvicorn server on PostgreSQL, end-to-end workflows | QA engineer |
| AI quality | Are AI outputs correct, consistent and honest? | Determinism, boundary and adversarial input, contract validation | QA engineer with the AI owner |
| Regression | Did a change break something that used to work? | Full suite before and after every merge | QA engineer |
| UAT | Can a real user complete the intended workflows? | Scripted live workflows against the deployed API | QA engineer with module owners |

---

## 4. Test environments

| ID | Environment | Purpose | Status |
|---|---|---|---|
| ENV-1 | Local, Python 3.10.11, SQLite in a temporary file | Fast regression loop, default CI-style run | Available |
| ENV-2 | Local, Python 3.10.11, PostgreSQL 16.15 on an isolated cluster (port 55432) | Production-dialect verification, JSONB, real constraints | Available |
| ENV-3 | Local Uvicorn server on `127.0.0.1:8011` backed by PostgreSQL `salesgenie_uat` | Live UAT, real HTTP | Available |
| ENV-4 | Docker Compose (api + postgres) | Deployment verification (SRS D-14) | **Blocked** - Docker daemon unavailable on the test machine |
| ENV-5 | Streamlit frontend + backend | UI integration and full E2E | **Blocked** - frontend not delivered |

Exact versions are recorded in [`evidence/2026-10-26-environment.txt`](evidence/2026-10-26-environment.txt).

### 4.1 Test data

* Automated tests build their own fixtures per test and roll back afterwards; no test
  depends on data left by another test.
* The live UAT run starts from a freshly migrated, empty database. The runner creates
  its own prospect, imports its own CSV and creates its own viewer account, so a
  re-run does not depend on the previous run.
* No production data and no real customer data is used. All names, companies and
  e-mail addresses are fictional (`*.example`).
* No credential used for testing is stored in this repository.

---

## 5. Entry and exit criteria

### 5.1 Entry criteria for a test cycle

1. The branch under test imports cleanly (`python -c "import main"`).
2. `requirements-dev.txt` installs into a clean virtual environment.
3. Alembic migrations apply to an empty database without error.
4. The application starts and `/api/v1/health` reports `status: ok`.

### 5.2 Exit criteria for the milestone

| # | Criterion | Target | Actual |
|---|---|---|---|
| 1 | All automated tests pass on SQLite | 100% | Met - 116 passed, 6 skipped |
| 2 | All automated tests pass on PostgreSQL | 100% | Met - 122 passed |
| 3 | No open Critical defects; every open High defect has an external blocker | 0 critical | Met - 0 critical; 2 High, both externally blocked (BUG-008, BUG-012) |
| 4 | Every Must-priority FR has a verdict | 100% | Met - see traceability matrix |
| 5 | Live UAT covers all six modules | 100% of workflows executed | Met - 21 workflows |
| 6 | Every failed or partial result is logged as a defect | 100% | Met - BUG-006 logged from UAT-15 |
| 7 | Deployment verified | Docker Compose starts | **Not met** - BUG-012, environment blocked |

Criterion 7 is the only unmet exit criterion. It is recorded as a known limitation, not
waived silently.

---

## 6. Defect management

### 6.1 Severity

| Severity | Definition |
|---|---|
| Critical | The application cannot start, or data is lost or corrupted |
| High | A Must-priority requirement is not met, or the system reports something untrue |
| Medium | A Should-priority requirement is not met, or a workflow is degraded with a workaround |
| Low | Cosmetic, documentation, or a gap with no user-visible impact |

### 6.2 Priority

Priority is business urgency, independent of severity: `P1` must be fixed before the
milestone, `P2` before the final delivery, `P3` when time allows.

### 6.3 Lifecycle

`New → Triaged → In progress → Fixed → Verified → Closed`, with `Deferred` and
`Won't fix` as terminal states. A defect is only `Closed` after the fix is re-tested and
the evidence is attached to the bug record.

---

## 7. Risk-based prioritisation

| Risk | Likelihood | Impact | Mitigation in this plan |
|---|---|---|---|
| Schema churn when the database owner's work is merged | High | High | Database tests assert both ORM metadata and migration output, so a divergence fails loudly |
| AI package absent from the integrated repository | High | High | External engine is exercised against a stub package; the gap is BUG-008 |
| Fabricated AI output presented as fact | Medium | High | Every AI test asserts the presence of `missing_information` or an explicit disclaimer |
| KPIs invented to fill a dashboard | Medium | High | Analytics tests assert `null` + `pending_definition` while D-10 is open |
| Frontend contract drift | Medium | Medium | API contract is frozen and documented; the contract is tested, not assumed |
| Deployment never verified | High | Medium | Recorded as an open defect with an explicit reason, never claimed as working |
| Test suite passes locally but not from a clean install | Medium | Medium | A clean virtual environment is built from `requirements-dev.txt` for every verification round |

---

## 8. Schedule against milestones

| Milestone | Date | QA activity | Deliverable |
|---|---|---|---|
| M1 | 20 Oct 2026 | Baseline audit, Module 1 and 2 test design | Baseline defect list (BUG-001, BUG-002, BUG-003) |
| M2 | 30 Oct 2026 | Module 3 and 4 verification, AI quality validation, regression | This pack |
| M3 | 10 Nov 2026 | Module 5 verification, CRM failure paths, integration tests | Updated pack + integration report |
| M4 | 20 Nov 2026 | UAT with the frontend, performance measurement, deployment verification | Final test report and sign-off |

---

## 9. Tools

| Tool | Use |
|---|---|
| `pytest` 9.1.1 | Unit, API, database and integration tests |
| `httpx` / Starlette `TestClient` | In-process API calls |
| `scripts/qa_uat.py` | Live HTTP UAT runner, writes Markdown and JSON evidence |
| Postman | Manual and exploratory API testing; collection in [`../../postman/`](../../postman) |
| Alembic | Migration up/down verification |
| `psql` | Direct database inspection |
| Git | Traceability from defect to commit |

---

## 10. Assumptions and dependencies

1. The API contract in [`../api-contract.md`](../api-contract.md) is the reference for the
   frontend. Any change to it requires a regression run and a contract update.
2. The database schema in the integrated repository is **provisional** until the database
   owner's work is merged. Database test cases will be re-run and re-baselined at that
   point.
3. Open SRS decisions D-05, D-06, D-09, D-10, D-11, D-12 and D-13 bound what can be
   verified. Where a decision is open, the test asserts honest behaviour (refusal,
   `null`, or `pending_definition`) rather than inventing a result.
4. Docker verification depends on a working daemon, which was not available on the test
   machine.
