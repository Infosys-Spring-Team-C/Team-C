# Milestone 3 QA & Test Engineering Completion Report

## SalesGenie AI — Module 5: CRM Integration & External Synchronization

**Author / Role:** Mohamed Isharak M, QA / Test Engineer and Project Lead\
**Execution period in schedule:** October 31–November 10, 2026 (Days 20–30)\
**Verification re-run:** 17–18 November 2026\
**Target milestone and module:** Milestone 3 — Module 5 (CRM Integration & External Synchronization)\
**Report prepared:** 18 November 2026

---

## 1. Document header and executive summary

The Milestone 3 schedule gives QA four touch points: Day 26 (finalise the external endpoints
and exercise the contact, activity and deal-stage workflows), Day 27 (summary quality review
with the AI/ML Engineer), Day 28 (draft the Milestone 3 test report with the Backend
Developer) and Day 30 (report submission and sign-off with the Project Lead). This report
records what was actually executed for those rows and what the evidence supports.

The QA pack is complete as a deliverable set for the milestone: a test plan, scenarios with
acceptance criteria, 81 test cases mapped to automated tests, API and database matrices, AI
quality validation, a regression procedure, a 20-entry defect log, a 25-workflow live UAT, a
traceability matrix and the formal Milestone 3 test report. Every result quoted here was
produced by running a command in this repository; nothing is estimated or copied from a plan.

Verified in this pass:

| Signal | Result |
|---|---|
| Test cases | **81** - 69 `PASS`, 2 `PARTIAL`, 2 `BLOCKED`, 8 `NOT RUN` |
| Automated suite, SQLite | **191 passed, 7 skipped** (198 collected), 18 Nov 2026; the 17 Nov run was 175/7 before the 16 transport tests |
| CRM live-transport tests | **16 passed**, no network call |
| Module 5 focused tests | **14 passed**, 45 deselected |
| Live UAT workflows | **25 passed, 0 partial, 0 failed** |
| Live AI integration gate (Groq) | **6/6 operations**, `used_mock=false` |
| Conversations page headless render | **PASS** - 7 sections, no exception |
| Defects | **20 total** - 18 closed, 2 open (both Low) |
| Requirements fully verified | **36 of 53** (7 `PARTIAL`, 9 `BLOCKED`, 1 `NOT RUN`) |
| Postman collection | **46 requests** in 9 folders, JSON validated |

Four honesty notes govern the numbers above:

1. **The UAT ran the deterministic heuristic engine**, not the live model, so the result is
   reproducible. The live Groq path is proven separately by the integration gate
   (6/6, `used_mock=false`) and is not claimed as part of the UAT run.
2. **The live CRM transport is implemented but has never been pointed at a real org.** SRS
   Decision D-06 still leaves CRM access unconfirmed. The transport is covered by 16 tests with
   the HTTP layer replaced by a fake, so mapping, retry and audit behaviour are proven, but
   vendor acceptance is not.
3. **The Conversations page was walked in a browser on 18 November 2026.** The data contract
   and a headless Streamlit render were already verified; the earlier browser attempt was
   blocked by host memory. The retry rendered every section with real stored data, no console
   errors and no horizontal overflow, so `FR-044` and `AC-023` move to `PASS`. A pixel
   screenshot was not captured, so styling at other viewports is not claimed.
4. **The 85% scoring-accuracy target is not claimed.** The metric and dataset are undefined
   (D-13). No accuracy, probability or satisfaction percentage is reported as achieved.

---

## 2. Milestone 3 deliverables and ownership matrix

| Day and date | SDLC phase | Scheduled task | Collaborating roles | QA deliverable and evidence |
|---|---|---|---|---|
| Day 21 · Sun, Nov 1 | Sprint planning | Sprint planning and summarisation prompt design | Project Lead + AI/ML | Test scope, levels and exit criteria recorded in `docs/qa/test-plan.md`. No separate meeting minutes exist. |
| Day 26 · Fri, Nov 6 | Testing & QA | Finalise external endpoints; exercise contact, activity and stage workflows; prepare sync test notes | Backend + QA | `TC-M5-*` cases in `docs/qa/test-cases.md`; UAT-22, UAT-23, UAT-24; API tests in `tests/test_api_ai.py`; PostgreSQL 16 run **177 passed** on the same day. |
| Day 27 · Sat, Nov 7 | Quality review | Review summary quality with the AI/ML Engineer | AI/ML + QA | `docs/qa/ai-quality-validation.md` and the grounding tests in `tests/test_intelligence.py`; no formal reviewer session is recorded, so quality is described as checked, not accepted. |
| Day 28 · Sun, Nov 8 | Buffer / Review | Prepare the demo, fix CRM issues, draft the Milestone 3 test report | QA + Backend | `docs/qa/milestone3-test-report.md` (drafted and later refreshed on 17 November); defect log maintained. |
| Day 29 · Mon, Nov 9 | Milestone Evaluation | Demo CRM integration and call summaries | Full Team | No demo build, recording, minutes or evaluation result exists. This report does not claim a session occurred. |
| Day 30 · Tue, Nov 10 | Submission / Sign-off | Report submission and sign-off | Project Lead + QA | Sign-off row in the Milestone 3 report is **pending**; the scheduled dates passed without a recorded session. |

The honest position is that the **verification work was executed and evidenced**, while the
**demo and sign-off rows were not completed**. The QA pack does not convert a missed
ceremony into a pass.

---

## 3. Test approach and core QA implementations

### 3.1 Levels and environments

| Level | How it is exercised | Environment |
|---|---|---|
| Unit | `pytest` modules for the summariser, scoring, schema and adapters | SQLite in-memory / temporary files |
| API | `TestClient` against the FastAPI app, positive and negative cases | SQLite; PostgreSQL for the dialect module |
| Database | ORM round-trip, keys, constraints, migration up/down, generated-DDL parity | SQLite and PostgreSQL 16 |
| Integration | API↔database, API↔AI engine, API↔frontend contract, container topology | Local server, Compose stack |
| Live UAT | 25 workflows over HTTP against a running server | SQLite file, heuristic engine |
| AI quality | Six-operation gate against the configured provider | Live Groq, and a documented SKIP path |
| Frontend render | Streamlit `AppTest` against the live API | Local server, headless |

The PostgreSQL module refuses to run unless `TEST_DATABASE_URL` names a `*test*` database,
because it drops and recreates the `public` schema.

### 3.2 Test design and traceability

* `docs/qa/test-scenarios.md` has one scenario block per module, each with acceptance
  criteria. Module 5 adds `SCN-M5-07` for the Conversations data contract.
* `docs/qa/test-cases.md` holds **81 cases**. Each row names the automated test or UAT
  workflow that proves it, so a verdict can be traced to an artefact.
* `docs/qa/traceability-matrix.md` maps 53 functional requirements to cases, tests and a
  verdict. Current split: **36 `PASS`, 7 `PARTIAL`, 9 `BLOCKED`, 1 `NOT RUN`**.
* `docs/qa/api-test-matrix.md` and `docs/qa/database-test-matrix.md` cover status codes,
  negative cases, constraints and migration behaviour; the importable Postman collection
  carries 46 requests.

### 3.3 Automation

| Suite | Command | Result |
|---|---|---|
| Canonical suite | `python -m pytest -q` | **175 passed, 7 skipped** |
| Module 5 focus | `pytest tests/test_api_ai.py tests/test_frontend_compat.py -k "crm or conversation"` | **14 passed**, 45 deselected |
| Contributor AI suite | `pytest -q` inside `contributions/mahidhar-ai-layer` | **86 passed** |
| Contributor backend suite | `pytest -q` inside `contributions/team-c-doran` | **24 passed, 1 failed** (BUG-020, owner action) |

The 7 skips are 6 PostgreSQL-only tests and 1 opt-in LangGraph memory-checkpointer test whose
optional extra is not installed. The only warning is the deliberate short-key JWT test.

`pytest.ini` at the repository root excludes `contributions/` from root collection
(BUG-019): the contributor archives have their own import roots and reuse module names. Each
contribution still runs from its own folder.

### 3.4 Live UAT harness

`scripts/qa_uat.py` drives the real HTTP API: it signs in, creates probe prospects, exercises
each module and deletes the probes. The Module 5 workflows are order-independent and leave no
residue. The 17 November run used an isolated SQLite file and the deterministic heuristic
engine so that the result can be reproduced exactly.

The Module 5 workflows added or re-run:

| ID | Workflow | Observed |
|---|---|---|
| UAT-22 | CRM field mappings for both providers | Salesforce `Account.Name` and HubSpot `dealstage` present; contact, activity and deal maps complete; unknown provider returns `422 invalid_provider`; `live_transport_available: false` |
| UAT-23 | Simulated sync across three workflows | `sync_contact` → contact, `activity_log` → activity, `update_stage` → deal; all `mode: simulated`; audit rows carry the right `entity_type` |
| UAT-24 | Unknown operation refused | `422 invalid_operation`; sync-log count unchanged; `/crm/status` reports `connectivity: simulated` |
| UAT-25 | Conversations page data contract | Stored interaction carries id, lead, type, date, summary, key points and action items |
| UAT-17 | Failed sync is safe (re-run) | `501 crm_not_configured`; log grew by one; the lead and its stored interaction are intact |

### 3.5 AI quality validation

* The deterministic tests assert **grounding**: a summary may only contain discussion points
  and action items that appear in the supplied transcript. An invented action item fails the
  suite.
* `scripts/check_ai_integration.py` exercises six operations. With the optional `openai` SDK
  installed and a Groq key configured, the 17 November run returned **6/6 operations passed**
  with `engine=external`, `used_mock=False`, including `summarize_conversation`.
* Without a key the provider falls back to the deterministic mock and labels every result
  `used_mock=true`. Without the `ai` package the gate exits `2` with a SKIP message rather
  than pretending to pass.
* No accuracy percentage is computed or claimed; the metric and dataset are still open under
  D-13.

### 3.6 Frontend verification and its limit

The page's data contract is verified end to end: every CRM route it calls resolves through
`frontend/api_compat.py` to the canonical API, and `tests/test_frontend_compat.py` fails if a
route stops resolving. A headless `AppTest` run then creates a probe prospect with one stored
summary and three simulated syncs and asserts that all seven Conversations sections reach the
rendered element tree - **PASS**.

The headless render was followed by a real browser walkthrough on 18 November 2026. The page
was opened in the in-app Chromium browser against a running API and Streamlit server with one
stored call summary and three simulated sync rows. Every section rendered, the stored data was
visible, there were no console errors and no horizontal overflow. A screenshot was not captured
because the desktop window was not visible to the tool, so pixel-level styling at other
viewports is not claimed. Evidence: `docs/qa/evidence/2026-11-18-browser-walkthrough.md`.

### 3.7 Defect management

| Severity | Open | Closed |
|---|---|---|
| Critical | 0 | 2 |
| High | 0 | 10 |
| Medium | 0 | 3 |
| Low | 2 (BUG-011, BUG-020) | 3 |
| **Total** | **2** | **18** |

* **BUG-019** (High, closed): adding the contributor archives broke bare `pytest` at the
  repository root. Fixed with a root `pytest.ini` that excludes `contributions/` from root
  collection.
* **BUG-020** (Low, open, owner action): the merged `contributions/team-c-doran` suite has
  one failing test. `test_delete_lead` calls the protected delete route without a token and
  expects `204`, receives `401`. It is a single incorrect test in a standalone contribution;
  the canonical application is unaffected, and QA did not edit the contributor's archive.
* **BUG-011** (Low, open, accepted limitation): follow-ups cannot be dismissed. `FR-052`
  requires the panel, which works; adding persisted dismissal state would change the schema.

---

## 4. Results

### 4.1 Automated tests

| Environment | Command | Result |
|---|---|---|
| SQLite (18 Nov 2026) | `python -m pytest -q` | **191 passed, 7 skipped** (198 collected) |
| CRM live transport | `pytest tests/test_crm_transport.py -q` | **16 passed**, fake HTTP layer, no network |
| SQLite (17 Nov 2026) | `python -m pytest -q` | **175 passed, 7 skipped** (182 collected) in 142.01 s |
| Module 5 focus | `pytest ... -k "crm or conversation"` | **14 passed**, 45 deselected |
| PostgreSQL 16 (6 Nov 2026) | `pytest -q` with `TEST_DATABASE_URL` | **177 passed, 0 skipped** (177-test suite at the time) - not repeated |
| Contributor AI suite | `pytest -q` in `contributions/mahidhar-ai-layer` | **86 passed** |
| Contributor backend suite | `pytest -q` in `contributions/team-c-doran` | **24 passed, 1 failed** - BUG-020 |
| Conversations render | `python scripts/qa_conversations_render.py` | **PASS** - 7 sections, no exception |
| Live AI gate (Groq) | `python scripts/check_ai_integration.py` | **6/6 operations**, `used_mock=false` |

### 4.2 Live UAT

| Metric | Value |
|---|---|
| Workflows | 25 |
| Passed | 25 |
| Partial | 0 |
| Failed | 0 |

### 4.3 Module 5 requirement verdicts

| Requirement | Verdict | Basis |
|---|---|---|
| FR-036 Summarise meeting and call notes | **PASS** | Persistence test, UAT-16 |
| FR-037 Extract key discussion points | **PASS** | Grounding test |
| FR-038 Extract action items | **PASS** | Explicit commitments only; no invention |
| FR-039 Store sales interactions | **PASS** | Persistence test, UAT-16, UAT-25 |
| FR-040 CRM field mapping | **PASS** (documented) | Both providers mapped; vendor confirmation still pending |
| FR-041 Sync contacts and activities | **PARTIAL** | Simulator plus opt-in live transport implemented; no sandbox run captured (D-06) |
| FR-042 Sync deal stage | **PARTIAL** | Simulator plus opt-in live transport implemented; no sandbox run captured (D-06) |
| FR-043 Record CRM sync logs | **PASS** | Attempt, outcome, entity type, timestamp, error, attempt count |
| FR-044 Conversations UI | **PASS** | Page, data contract and headless render verified; browser walkthrough on 18 Nov 2026 rendered every section with stored data, no console errors and no overflow. Pixel styling not screenshotted |
| FR-045 Failure keeps the local record | **PASS** | Failure test, UAT-17 |

Acceptance criteria `AC-021` to `AC-025` all pass. `AC-023` is supported by the stored data, the
headless render and the 18 November browser walkthrough.

### 4.4 Evidence index

| Artefact | Path |
|---|---|
| Environment and versions | `docs/qa/evidence/2026-11-17-environment.txt` |
| Pytest, SQLite (175 passed) | `docs/qa/evidence/2026-11-17-pytest-sqlite.txt` |
| Pytest, Module 5 focused (14 passed) | `docs/qa/evidence/2026-11-17-pytest-module5-focused.txt` |
| Pytest, CRM live transport (16 passed) | `docs/qa/evidence/2026-11-18-pytest-crm-transport.txt` |
| Live UAT, 25/25 (Markdown) | `docs/qa/evidence/2026-11-17-uat-live-milestone3.md` |
| Live UAT, 25/25 (JSON) | `docs/qa/evidence/2026-11-17-uat-live-milestone3.json` |
| Conversations headless render (PASS) | `docs/qa/evidence/2026-11-17-conversations-headless-render.txt` |
| Browser walkthrough (PASS, 18 Nov) | `docs/qa/evidence/2026-11-18-browser-walkthrough.md` |
| Browser walkthrough attempt (BLOCKED, 17 Nov) | `docs/qa/evidence/2026-11-17-browser-walkthrough-attempt.md` |
| AI gate attempt without SDK (documented SKIP) | `docs/qa/evidence/2026-11-17-ai-integration-gate.txt` |
| AI gate, 6/6 live Groq (17 Nov) | `docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt` |
| Contributor backend suite (24 passed, 1 failed) | `docs/qa/evidence/2026-11-17-pytest-doran-contribution.txt` |
| Schema parity (110 columns, 6 FKs, 31 indexes) | `docs/qa/evidence/2026-10-26-schema-parity.txt` |
| PostgreSQL 16 (177 passed, 6 Nov) | `docs/qa/evidence/2026-11-06-pytest-postgres.txt` |
| Compose verification (27 Oct) | `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| Frontend integration gate (12/12, 27 Oct) | `docs/qa/evidence/2026-10-27-frontend-integration-gate.txt` |
| Clean install (37 frontend-adapter tests passed, 27 Oct) | `docs/qa/evidence/2026-10-27-clean-install.txt` |

---

## 5. What does not work, or was not verified

| # | Limitation | Why | Consequence |
|---|---|---|---|
| 1 | No verified live CRM synchronisation | Transport implemented; no sandbox or credentials supplied (D-06) | `FR-041`/`FR-042` stay `PARTIAL` until a captured live run |
| 2 | Field maps not confirmed against a real org | No sandbox org available | Maps use documented vendor field names; a CRM admin must confirm custom fields |
| 3 | Pixel-level styling at other viewport sizes not judged | The 18 Nov browser walkthrough captured DOM text and layout metrics, but the desktop window was not visible to the screenshot tool | `FR-044`/`AC-023` pass on functional presentation; no aesthetic or responsive claim is made |
| 4 | PostgreSQL not re-run this pass | Docker and the local cluster unavailable | SQLite result is current; PostgreSQL evidence is from 6 November 2026 |
| 5 | Compose stack not rebuilt this pass | Same | Last verification 27 October 2026 |
| 6 | No accuracy or satisfaction figure | Metric and survey undefined (D-12, D-13) | The 85% targets are not claimed as achieved |
| 7 | Summarisation quality not formally reviewed | No rubric session with the AI/ML Engineer | Output is checked for grounding and structure, not for sales-team usefulness |
| 8 | No performance figure | Measurement conditions undefined (D-11) | No latency claim is made |

---

## 6. Risk assessment for the milestone demonstration

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A reviewer asks to see a real Salesforce/HubSpot sync | High | Medium | Explain D-06; show the labelled simulator, the field map and the audit rows |
| A reviewer asks whether the UI was checked | Low | Low | Show the 18 Nov browser walkthrough (all sections, stored data, no console errors); state that pixel styling was not screenshotted |
| A reviewer asks for a live model call | Low | Low | Show the 17 November gate (6/6, `used_mock=false`, live Groq) and the health metadata |
| A reviewer asks why PostgreSQL was not used | Medium | Low | Show `tests/test_postgres.py` and the 6 November run; state the environment limitation |
| A summary omits an action item a reviewer expects | Medium | Low | The engine only extracts explicit commitments; demonstrate with a transcript that states them |
| A reviewer asks for the 85% accuracy figure | Medium | Medium | State that the metric and dataset are undefined (D-13) and no figure is claimed |

---

## 7. Conclusion and transition to Milestone 4

The QA deliverables for Module 5 are complete and evidenced:

* 81 test cases with traceability, and a 25-workflow live UAT that passed in full;
* the canonical suite green on SQLite, with a PostgreSQL result from 6 November;
* a live AI gate at 6/6 with `used_mock=false`, and grounding tests that reject invented
  content;
* a Conversations render check plus an 18 November browser walkthrough that rendered every
  section with stored data, no console errors and no overflow;
* 20 logged defects with 2 open, both Low, and neither hidden.

What remains for the final phase is not new test design but closing the environment gaps:
rebuild the Compose stack and re-run the PostgreSQL suite on a host with a working Docker
daemon, obtain the D-12 and D-13 definitions before any accuracy or satisfaction figure is
quoted, capture a live CRM sandbox run, and complete the demo and sign-off rows that the
schedule places on 9–10 November 2026.

---

**Evidence note:** This report is based on the repository state on 18 November 2026
(`main` at `825cc1c` plus these report files) and the captured artefacts under
`docs/qa/evidence/`. The UAT ran the deterministic heuristic engine; the live Groq result
comes from the separate six-operation gate. The Conversations page was walked in a browser on
18 November 2026, but no pixel screenshot was captured. No live CRM call, PostgreSQL re-run,
accuracy percentage or satisfaction score is claimed for this pass.
