# Milestone 3 Test Report - Module 5 (Conversation Intelligence and CRM Integration)

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Report date:** 18 November 2026 (first issued 17 November 2026; CRM live transport and
browser walkthrough added on 18 November)
**Prepared by:** Mohamed Isharak M - QA / Test Engineer
**Repository:** `Infosys-Spring-Team-C/Team-C`
**Build under test:** `main` at `825cc1c` (CRM live transport, 16 new tests, CI workflow),
plus the QA tooling and documentation added in this pass (`pytest.ini`, the four Module 5 UAT
workflows and the refreshed QA pack).
**Milestone:** M3 evaluation (Module 5 demonstrated; Modules 1-6 integrated)

---

## 1. Executive summary

Module 5 is **implemented, tested and safe to demonstrate**. The build summarises meeting
and call notes, extracts discussion points and action items, stores every interaction, maps
SalesGenie fields onto Salesforce and HubSpot, runs a clearly-labelled CRM sync simulator
for contacts, activities and deal stages, and writes an audit row for every attempt.

| Signal | Result |
|---|---|
| Canonical pytest suite (SQLite) | **191 passed, 7 skipped** (18 Nov 2026) |
| CRM live-transport tests | **16 passed**, no network |
| Module 5 focused tests | **14 passed** - 10 CRM-related (9 API + 1 adapter), 4 conversation-related (3 API + 1 adapter) |
| Module 5 backend routes | **12 implemented** - 8 CRM, 4 conversation |
| Live UAT workflows | **25 passed, 0 partial, 0 failed** |
| Live AI integration gate (Groq) | **6/6 operations**, `used_mock=false` |
| Conversations page render (headless) | **PASS** - 7 sections, no exception |
| Conversations page browser walkthrough | **PASS** - every section rendered, 0 console errors, no horizontal overflow (18 Nov 2026) |
| Defects found this pass | 2 (BUG-019 closed; BUG-020 open) |
| Defects open | 2 (BUG-011 and BUG-020, both Low) |
| Requirements fully verified (FR-036 to FR-045) | 8 of 10 |
| Requirements partly verified | 2 of 10 - both blocked by D-06 (live CRM transport) |

Three limits are stated openly and are **not** presented as achievements:

1. **No live Salesforce or HubSpot call has been made.** Decision D-06 leaves CRM access
   unconfirmed. A live transport is now implemented
   (`backend/services/crm_transport.py`) and is opt-in behind `CRM_LIVE_ENABLED=true` plus
   credentials, but it has never been pointed at a real org. What is verified is a
   provider-neutral payload mapping, a documented field map for both vendors, a deterministic
   simulator that writes real audit rows, and 16 transport tests with a fake HTTP layer. The
   simulator is labelled `mode: "simulated"` in the response and in the database, and its note
   says that no Salesforce or HubSpot request was made.
2. **The PostgreSQL run and the Docker rebuild were not repeated.** Docker was unavailable
   on the test machine on 17 and 18 November 2026. The last PostgreSQL run (177 passed)
   and the last Compose verification are from 6 November and 27 October 2026 respectively
   and are cited as such.
3. **The browser walkthrough was completed on 18 November 2026, after the 17 November
   memory failure was cleared.** The Conversations page was opened in the in-app Chromium
   browser against a running API and Streamlit server with real stored data: all sections
   rendered, no console errors and no horizontal overflow. A pixel screenshot was not captured
   because the desktop window was not visible to the screenshot tool, so styling at other
   viewport sizes is still unjudged. Evidence:
   `docs/qa/evidence/2026-11-18-browser-walkthrough.md`.

A fourth honesty note: the UAT workflows in this pass ran the deterministic heuristic engine so
that the results are reproducible. The live Groq path is proven separately: after installing
the optional `openai` SDK, the integration gate returned **6/6 operations passed** with
`used_mock=false` on 17 November 2026, including `summarize_conversation`. The UAT itself did
not call the live model, and the report does not claim that it did.

---

## 2. What was tested

| Layer | Coverage | Result |
|---|---|---|
| Unit - summarisation engine, grounding, empty input | `tests/test_intelligence.py` | PASS |
| API - conversations, summaries, storage and read-back | `tests/test_api_ai.py` | PASS |
| API - CRM providers, field maps, validation, preview, sync, logs, retry, status | `tests/test_api_ai.py` | PASS |
| Frontend contract - every CRM route the page calls | `tests/test_frontend_compat.py` | PASS |
| Frontend render - Conversations page through Streamlit `AppTest` | `scripts/qa_conversations_render.py` | PASS (7 sections, no exception) |
| Database - `sales_interactions`, `crm_sync_logs`, entity type, JSON metadata | `tests/test_schema.py`, `tests/test_postgres.py` | PASS (SQLite this pass) |
| Integration - API to AI engine, API to database, API to frontend | suite + live UAT | PASS |
| Live UAT - 25 workflows over HTTP | `scripts/qa_uat.py` | 25/25 PASS |
| Live AI gate - six operations against Groq | `scripts/check_ai_integration.py` | 6/6 PASS, `used_mock=false` |
| Regression - full suite after the QA changes | `pytest -q` | PASS |
| Deployment - Docker build and Compose | not run | NOT RUN - daemon unavailable |

---

## 3. Results

### 3.1 Automated tests

| Environment | Command | Result |
|---|---|---|
| SQLite (this pass) | `python -m pytest -q` | **191 passed, 7 skipped** (198 collected) on 18 Nov; the 17 Nov run was 175/7 before the transport tests |
| CRM live transport | `pytest tests/test_crm_transport.py -q` | **16 passed**, fake HTTP layer, no network |
| Module 5 focus | `pytest tests/test_api_ai.py tests/test_frontend_compat.py -k "crm or conversation"` | **14 passed**, 45 deselected |
| PostgreSQL 16 (6 Nov 2026) | `pytest -q` with `TEST_DATABASE_URL` | **177 passed, 0 skipped** - not repeated |
| Contributor AI suite | `pytest -q` inside `contributions/mahidhar-ai-layer` | **86 passed** |
| Conversations render | `python scripts/qa_conversations_render.py` | **PASS** - 7 sections, no exception |
| Live AI gate (Groq) | `python scripts/check_ai_integration.py` | **6/6 operations**, `used_mock=false` |

Of the 7 skips, 6 are PostgreSQL-only tests and 1 is the opt-in LangGraph
memory-checkpointer test whose optional extra is not installed. The only warning is the
deliberate short-key JWT test.

The AI gate ran with the optional `openai` SDK installed and
`SALES_GENIE_LLM_PROVIDER=groq` / `SALES_GENIE_LLM_MODEL=openai/gpt-oss-120b`; every operation
reported `engine=external`, `used_mock=False`, including `summarize_conversation`.

Evidence: `docs/qa/evidence/2026-11-17-pytest-sqlite.txt`,
`docs/qa/evidence/2026-11-17-pytest-module5-focused.txt`,
`docs/qa/evidence/2026-11-17-conversations-headless-render.txt`,
`docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt`.

### 3.2 Live user acceptance

| Metric | Value |
|---|---|
| Workflows | 25 |
| Passed | 25 |
| Partial | 0 |
| Failed | 0 |

The five new workflows are:

| ID | Workflow | Observed |
|---|---|---|
| UAT-22 | CRM field mappings for both providers | Salesforce `Account.Name` and HubSpot `dealstage` present; contact, activity and deal maps complete; unknown provider `422 invalid_provider`; `live_transport_available: false` |
| UAT-23 | Simulated sync across the three workflows | `sync_contact` -> contact, `activity_log` -> activity, `update_stage` -> deal; all `mode: simulated`; audit rows persisted with the right `entity_type` |
| UAT-24 | Unknown operation refused | `422 invalid_operation`; sync-log count unchanged; `/crm/status` reports `connectivity: simulated` |
| UAT-25 | Conversations page data contract | Stored interaction carries id, lead, type, date, summary, key points and action items |
| UAT-17 | Failed sync is safe (re-run) | `501 crm_not_configured`, log grew by one, lead intact |

The Module 5 workflows create and delete their own probe prospects, so they are order
independent and leave no residue.

Evidence: `docs/qa/evidence/2026-11-17-uat-live-milestone3.md` and `.json`.

The UAT ran the deterministic heuristic engine (`SALES_GENIE_AI_BACKEND=heuristic`) so the
results are reproducible. The live Groq path is proven separately by the integration gate
(6/6 operations, `used_mock=false`) and not by this UAT run.

### 3.3 Module 5 requirement verdicts

| Requirement | Verdict | Evidence |
|---|---|---|
| FR-036 Summarise meeting and call notes | **PASS** | `test_conversation_summary_persists_interaction`, UAT-16 |
| FR-037 Extract key discussion points | **PASS** | `test_conversation_summary_extracts_only_supplied_action_items` |
| FR-038 Extract action items | **PASS** | Same test; `action_items` asserted, no invention |
| FR-039 Store sales interactions | **PASS** | `test_conversation_summary_persists_interaction`, UAT-16, UAT-25 |
| FR-040 CRM field mapping | **PASS** (documented) | `test_crm_field_mappings_are_documented_for_both_providers`, UAT-22. Vendor confirmation is still pending, so the map is documentation-grade, not org-validated |
| FR-041 Sync contacts and activities | **PARTIAL** | Simulator covers `sync_contact`, `activity_log` and `upsert`; the opt-in live transport is implemented and unit-tested, but no sandbox run exists (D-06). `test_crm_simulation_covers_contact_activity_and_stage`, `tests/test_crm_transport.py`, UAT-23 |
| FR-042 Sync deal stage | **PARTIAL** | Simulator covers `update_stage` -> deal record; the live transport maps deal stages and is unit-tested, but no sandbox run exists (D-06) |
| FR-043 Record CRM sync logs | **PASS** | Attempt, outcome, entity type, timestamp, error detail and attempt count; `test_crm_simulation_covers_contact_activity_and_stage`, UAT-23 |
| FR-044 Conversations UI | **PASS** | Page renders in a browser with notes entry, summary, key points, action items, CRM status, field map, sync form, activity feed and history; stored data displayed, no console errors, no horizontal overflow (`docs/qa/evidence/2026-11-18-browser-walkthrough.md`). Pixel-level styling at other viewports is unjudged |
| FR-045 Failure keeps the local record | **PASS** | `test_failed_crm_sync_keeps_the_local_interaction`, UAT-17 |

Acceptance criteria `AC-021` to `AC-025` all pass. `AC-023` is supported by the stored data, the
headless render and the 18 November browser walkthrough.

### 3.4 Module 5 schedule items

| # | Planned item | State |
|---|---|---|
| 1 | FastAPI endpoints for CRM integration | Done - providers, field maps, validation, preview, sync, status, logs, retry |
| 2 | CRM sync logic and `CRM_Sync_Logs` | Done - four operations, audit rows, entity type, retry |
| 3 | Meeting/call summarisation stored in `Sales_Interactions` | Done - summary, key points, action items, sentiment, follow-up date |
| 4 | Streamlit Conversations tab | Done in code - CRM sync status, meeting summary, field mapping, recent activity, history |
| 5 | Finalise endpoints and test the three CRM workflows | Done - automated tests and UAT-22 to UAT-24 |
| 6 | Review summarisation quality | Not formally reviewed; deterministic engine output checked for grounding only |
| 7 | Weekend buffer / catch-up | Not recorded |
| 8 | Demo build and draft report | This report is the draft; demo build blocked by Docker |
| 9 | Infosys demo and sign-off (9-10 Nov) | Not completed; no session ran |

### 3.5 Defects

| Severity | Open | Closed |
|---|---|---|
| Critical | 0 | 2 |
| High | 0 | 10 |
| Medium | 0 | 3 |
| Low | 2 (BUG-011, BUG-020) | 3 |
| **Total** | **2** | **18** |

Found and closed in this pass:

* **BUG-019** - adding the contributor archives under `contributions/` broke bare `pytest`
  at the repository root. Mahek's suite imports a local `database` package, and two suites
  share the basename `test_scoring.py`, so collection aborted before a single test ran.
  Fixed with a root `pytest.ini` that excludes `contributions/` from root collection; each
  contribution still runs from its own folder. Verified: 182 collected, 175 passed, 7
  skipped; Mahidhar's 86 tests still pass in place.

Found open in this pass:

* **BUG-020** - the newly merged `contributions/team-c-doran` suite reports 24 passed, 1
  failed. `test_delete_lead` calls `DELETE /leads/{lead_id}` without a token while the
  endpoint requires a manager or admin role, so it gets `401` instead of `204`. It is a
  single incorrect test in a standalone contribution; the canonical application is
  unaffected. Left as an owner action rather than edited in QA.

No Module 5 functional defect was found. The two failures seen during the first UAT attempt
were defects in the new UAT assertions, not in the application: a case-sensitive substring
check and an assertion on `created_at` where the API contract field is `interaction_date`
(the adapter maps it). Both assertions were corrected and the run is green.

### 3.6 Backend implementation status

The canonical backend contains the full Module 5 API surface. This is an implementation
statement, not a new verdict on `FR-041` and `FR-042`, which stay `PARTIAL`.

| Group | Routes | Notes |
|---|---|---|
| CRM | `GET /crm/providers`, `GET /crm/field-mappings`, `POST /crm/mappings/validate`, `POST /crm/sync/preview`, `POST /crm/sync`, `GET /crm/status`, `GET /crm/sync-logs`, `POST /crm/sync-logs/{log_id}/retry` | 8 routes; sync and retry require the writer role; `POST /crm/sync` uses the simulator, an opt-in live transport, or `501 crm_not_configured` |
| Conversations | `POST /conversations/summarize`, `POST /leads/{lead_id}/conversations`, `GET /leads/{lead_id}/conversations`, `GET /conversations/{interaction_id}` | 4 routes; writes require a writer role; reads are authenticated |

The earlier backend snapshot under `contributions/team-c-doran/reports/` lists conversation
storage and the Conversations UI as missing. That is true of that standalone snapshot and
not of the canonical repository, where `sales_interactions`, the four conversation routes and
the page are present and tested. No `TODO`, `FIXME` or `NotImplementedError` remains in the
Module 5 backend modules.

Full implementation detail: [`../reports/Milestone 3 report - Backend.md`](../reports/Milestone%203%20report%20-%20Backend.md).

---

## 4. What works, demonstrably

1. **Summarisation.** A transcript becomes an executive summary, discussion points and
   action items, and the interaction is persisted against the prospect with its type and
   date.
2. **Grounding.** The engine only reports commitments that appear in the text. Empty input
   is refused with a clear message; no commitment is invented.
3. **Storage and read-back.** `sales_interactions` rows are listable per lead and readable
   individually.
4. **Field mapping.** Salesforce and HubSpot maps exist for contact, activity and deal
   records, and the API reports `live_transport_available: false` rather than implying a
   connector.
5. **Simulated sync.** Contact, activity and deal-stage operations each produce the right
   provider-neutral record type and a `mode: simulated` response with an explicit
   no-external-call note.
6. **Audit.** Every attempt - simulated success or refused live call - writes a
   `crm_sync_logs` row with provider, entity type, operation, status, error and attempt
   count. Retry increments the attempt count and refuses to retry a success.
7. **Rejection path.** An unknown operation or provider is refused with `422` and writes no
   audit row.
8. **Failure safety.** A failed sync leaves the lead and its stored interaction untouched.
9. **Conversations page data and render.** The page's five data sources - conversation list,
   CRM status, field map, sync logs and the sync action - all resolve through
   `frontend/api_compat.py` to the canonical API, and a headless `AppTest` run confirms the
   seven sections reach the rendered element tree with live data.
10. **Frontend discipline.** The page states that the transport is simulated; no accuracy,
    probability or live-CRM claim is rendered.

---

## 5. What does not work, or was not verified

| # | Limitation | Why | Consequence |
|---|---|---|---|
| 1 | No verified live CRM synchronisation | Transport implemented; no sandbox or credentials supplied (D-06) | Simulator and audit rows verified; `FR-041`/`FR-042` stay `PARTIAL` |
| 2 | Field maps not confirmed against a real org | No sandbox org available | Maps use documented vendor field names; a CRM admin must confirm custom fields |
| 3 | Pixel-level visual styling at other viewport sizes was not judged | The 18 Nov browser walkthrough captured DOM text and layout metrics, but the desktop window was not visible to the screenshot tool | `FR-044`/`AC-023` pass on functional presentation; no claim is made about aesthetics or responsive styling |
| 4 | PostgreSQL not re-run this pass | Docker and the local cluster unavailable | SQLite result is current; PostgreSQL evidence is from 6 November 2026 |
| 5 | Compose stack not rebuilt this pass | Same | Last verification 27 October 2026 |
| 6 | Summarisation quality not formally reviewed | No rubric or reviewer session | Output is checked for grounding and structure, not for sales-team usefulness |
| 7 | No performance figure | Measurement conditions undefined (D-11) | No latency claim is made |
| 8 | No UAT satisfaction score | Survey undefined (D-12) | No satisfaction percentage is claimed |

---

## 6. Quality observations

**Strengths**

* The Module 5 tests are behavioural: they assert the record type produced by each
  operation, the audit row's entity type and the failure path, not just status codes.
* The honesty rule is enforced by tests. A simulator that claimed a live call, a fabricated
  probability or an invented accuracy figure would fail the suite.
* The UI contract test fails if a CRM route stops resolving to the canonical API, which is
  the failure mode that matters most for a thin Streamlit client.
* The UAT workflows are order independent and clean up after themselves.
* The new `pytest.ini` makes the regression command reliable again after the contributor
  archives landed (BUG-019).

**Weaknesses**

* No one has judged the Conversations screen. A correct data contract does not prove a
  usable layout.
* The simulator proves the mapping and the audit trail, not the vendor's acceptance of the
  payload.
* The suite is behavioural, not line-based; no coverage percentage is reported.
* There is still no CI workflow, so the suite is run by hand.

---

## 7. Risk assessment for the milestone demonstration

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A reviewer asks to see a real Salesforce/HubSpot sync | High | Medium | Explain D-06; show the labelled simulator, the field map and the audit rows |
| A reviewer asks whether the UI was checked | Low | Low | Show the 18 November browser walkthrough (all sections rendered, no console errors, no overflow); say that pixel styling was not screenshotted |
| A reviewer asks for a live model call | Low | Low | Show the 17 November gate (6/6, `used_mock=false`, live Groq) and the health metadata |
| A reviewer asks why PostgreSQL was not used | Medium | Low | Show `tests/test_postgres.py` and the 6 November run; state the environment limitation |
| A summary omits an action item a reviewer expects | Medium | Low | The engine only extracts explicit commitments; demonstrate with a transcript that states them |
| A typo in an operation name is sent | Low | Low | `422 invalid_operation`, no audit row - covered by UAT-24 |

---

## 8. Evidence index

| Artifact | Path |
|---|---|
| Environment and versions | `docs/qa/evidence/2026-11-17-environment.txt` |
| Pytest, SQLite (175 passed) | `docs/qa/evidence/2026-11-17-pytest-sqlite.txt` |
| Pytest, Module 5 focused (14 passed) | `docs/qa/evidence/2026-11-17-pytest-module5-focused.txt` |
| Live UAT, 25/25 (Markdown) | `docs/qa/evidence/2026-11-17-uat-live-milestone3.md` |
| Live UAT, 25/25 (JSON) | `docs/qa/evidence/2026-11-17-uat-live-milestone3.json` |
| Conversations page headless render (PASS) | `docs/qa/evidence/2026-11-17-conversations-headless-render.txt` |
| Browser walkthrough (PASS, 18 Nov) | `docs/qa/evidence/2026-11-18-browser-walkthrough.md` |
| Browser walkthrough attempt (BLOCKED, 17 Nov) | `docs/qa/evidence/2026-11-17-browser-walkthrough-attempt.md` |
| AI integration gate attempt (documented SKIP, no SDK) | `docs/qa/evidence/2026-11-17-ai-integration-gate.txt` |
| AI integration gate, 6/6 live Groq (17 Nov) | `docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt` |
| AI integration gate, 6/6 live Groq (6 Nov) | `docs/qa/evidence/2026-11-06-ai-integration-gate-live-groq.txt` |
| Pytest, PostgreSQL 16 (177 passed, 6 Nov) | `docs/qa/evidence/2026-11-06-pytest-postgres.txt` |
| Docker Compose verification (27 Oct) | `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| Contributor backend suite (24 passed, 1 failed - BUG-020) | `docs/qa/evidence/2026-11-17-pytest-doran-contribution.txt` |
| Traceability | [`traceability-matrix.md`](traceability-matrix.md) |
| Test cases | [`test-cases.md`](test-cases.md) |
| API matrix | [`api-test-matrix.md`](api-test-matrix.md) |
| Regression suite | [`regression-suite.md`](regression-suite.md) |
| UAT plan and results | [`uat-plan.md`](uat-plan.md), [`uat-results.md`](uat-results.md) |
| Defect log | [`bug-log.md`](bug-log.md) |
| Scenarios | [`test-scenarios.md`](test-scenarios.md) |
| Integration plan | [`integration-test-plan.md`](integration-test-plan.md) |

---

## 9. Recommendation

**Recommendation: demonstrate Module 5 with the limitations in section 5 stated openly.**

Conditions:

1. Show the Conversations page with a transcript that contains explicit commitments, so the
   summary, key points and action items are visibly grounded.
2. Show the field map for both providers and say that the names are documented vendor
   fields, not org-confirmed custom fields.
3. Run the simulator for `sync_contact`, `activity_log` and `update_stage`, then show the
   audit rows and the `mode: simulated` note. Do not describe it as a live sync.
4. Show the refused operation (`422 invalid_operation`) and the refused live sync (`501`).
   Both are deliberate and both are tested.
5. Do not claim a live CRM call, a PostgreSQL run or a live model call that did not happen in
   this pass. The 18 November browser walkthrough was executed and may be described as such;
   pixel-level styling was not screenshotted, so do not claim a visual design review.
6. Re-run the full suite, the UAT and the render check after any further merge, and update
   this report.

---

## 10. Sign-off

| Role | Name | Status |
|---|---|---|
| QA / Test Engineer | Mohamed Isharak M | Signed - 17 November 2026 |
| Backend owner | M Doran | Pending |
| Database owner | Marri Sai Surekha | Pending - PostgreSQL re-run required |
| AI owner | Mahidhar Reddy | Pending - summarisation quality review outstanding |
| Frontend owner | Maheksaba Akbar Shaikh | Done - browser walkthrough 18 Nov 2026 (pixel styling not screenshotted) |
