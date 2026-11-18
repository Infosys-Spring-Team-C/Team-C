# Milestone 3 - QA and Test Engineering Contribution

**Contributor:** Mohamed Isharak M, QA / Test Engineer and Project Lead\
**Module:** Milestone 3 - Module 5 (CRM Integration & External Synchronization)\
**Date:** 18 November 2026

---

## 1. Test scope for Module 5

Module 5 adds conversation summarisation and CRM synchronisation. Both are risky in a specific
way: one can invent content, and the other can claim an integration that never happened. The
test work was designed around those two risks.

The scope covered functional requirements `FR-036` to `FR-045` and acceptance criteria `AC-021`
to `AC-025`:

| Area | Requirements |
|---|---|
| Conversation summarisation | `FR-036`, `FR-037`, `FR-038`, `FR-039` |
| CRM field mapping | `FR-040` |
| CRM synchronisation | `FR-041`, `FR-042`, `FR-043`, `FR-045` |
| Conversations UI | `FR-044` |

The QA deliverables for the milestone are 81 test cases, 35 test scenarios, a 25-workflow live
UAT, a defect log, a traceability matrix and a regression procedure.

---

## 2. Test approach

### 2.1 Layers

| Layer | What it exercises | Why it exists |
|---|---|---|
| Unit and API tests | Route behaviour, validation, RBAC, persistence | Fast feedback on every change |
| Frontend contract tests | Every route the UI calls, through `frontend/api_compat.py` | Catches a route rename before the UI breaks |
| Live UAT over HTTP | A running server, real sign-in, real requests | Proves the deployed contract, not just imported functions |
| Headless Streamlit render | The page's element tree with live data | Proves the page receives and renders every section |
| Browser walkthrough | The page in a real browser with stored data | Proves layout and console behaviour |
| AI integration gate | Six operations against the live provider | Proves the real provider path, not the mock |

### 2.2 Why the layers are separate

No single layer can answer all the questions. An API test cannot show that a Streamlit page
renders; a render test cannot show that the browser has no console error; a browser check cannot
show that RBAC rejects a viewer. Each layer answers one question and the evidence names the layer
that produced it.

The split also prevents a common overstatement: a passing API test is reported as an API test,
never as "the UI works".

### 2.3 Traceability

Every requirement row in `docs/qa/traceability-matrix.md` names the test case, the automated test
and the UAT workflow that verifies it. `docs/qa/test-cases.md` holds the 81 cases; each row points
at the test or workflow that executes it.

---

## 3. Module 5 coverage

### 3.1 Requirement coverage

| Requirement | Verified behaviour | Evidence |
|---|---|---|
| `FR-036` Summarise meeting notes | Summary persisted against the lead | `test_conversation_summary_persists_interaction`, UAT-16 |
| `FR-037` Extract key discussion points | Only supplied points are returned | `test_conversation_summary_extracts_only_supplied_action_items` |
| `FR-038` Extract action items | `action_items` matches explicit commitments | Same test, asserted field by field |
| `FR-039` Store sales interactions | Interaction row carries lead, type, date and summary | `test_conversation_summary_persists_interaction` |
| `FR-040` CRM field mapping | Maps documented for Salesforce and HubSpot | `test_crm_field_mappings_are_documented_for_both_providers`, UAT-22 |
| `FR-041` Sync contacts and activities | `sync_contact`, `activity_log` and `upsert` mapped and executed | `test_crm_simulation_covers_contact_activity_and_stage`, UAT-23, 16 transport tests |
| `FR-042` Sync deal stage | `update_stage` produces a deal record with the mapped stage | Same test, `update_stage` branch |
| `FR-043` Record sync logs | Attempt, outcome, entity type, timestamp, error and attempt count | `test_crm_sync_records_failure_and_retry`, UAT-23 |
| `FR-044` Conversations UI | Page renders every section with stored data | Contract test, headless render, browser walkthrough |
| `FR-045` Failure keeps the local record | A failed sync leaves the lead and interaction intact | `test_failed_crm_sync_keeps_the_local_interaction`, UAT-17 |

### 3.2 Acceptance criteria

`AC-021` to `AC-025` are covered by the Module 5 cases:

| Criterion | Verified by |
|---|---|
| `AC-021` Notes produce summary, points and actions | `TC-M5-001` to `TC-M5-003` |
| `AC-022` Empty or invalid notes give a clear message, no fabrication | `TC-M5-005`, `TC-M5-006` |
| `AC-023` Interactions stored and listed in the UI | `TC-M5-004`, `TC-M5-014`, `TC-M5-015`, browser walkthrough |
| `AC-024` Sync attempts, successes and failures logged | `TC-M5-008`, `TC-M5-011`, `TC-M5-012` |
| `AC-025` Failed sync does not delete or corrupt the local record | `TC-M5-009` |

### 3.3 Test case results

| Module 5 cases | Result |
|---|---|
| 15 cases (`TC-M5-001` to `TC-M5-015`) | **15 passed** |

---

## 4. Automated coverage

### 4.1 Module 5 focused suite

| Signal | Result |
|---|---|
| CRM-related tests | 10 (9 API, 1 adapter) |
| Conversation-related tests | 4 (3 API, 1 adapter) |
| Total focused run | **14 passed**, 45 deselected |

The focused run is the fast loop used while changing Module 5 code.

### 4.2 CRM live-transport tests

`tests/test_crm_transport.py` adds **16 tests** covering the live transport:

| Group | Tests | What is asserted |
|---|---|---|
| Payload mapping | 5 | Salesforce `Lead`/`Task`/`Opportunity` and HubSpot `contacts`/`tasks`/`deals` field sets; required fields; unknown record type refused |
| Retry behaviour | 3 | Transient failure retried then succeeds; retry stops at `max_attempts`; non-retryable failure is not repeated |
| Configuration | 3 | Live transport off by default; credentials alone do not enable it; flag plus credentials builds a transport |
| Route behaviour | 4 | Live success writes a `mode: live` audit row; failure returns `502` and is audited; unconfigured call keeps `501`; providers report real availability |

The HTTP layer is replaced by a fake, so the suite never opens a socket. That is a deliberate
rule: a unit suite must not mutate a real CRM.

### 4.3 Full suite

| Environment | Result |
|---|---|
| SQLite, 18 November 2026 | **191 passed, 7 skipped** (198 collected) |
| PostgreSQL 16, 6 November 2026 | **177 passed, 0 skipped** |

The 7 SQLite skips are 6 PostgreSQL-only tests and one opt-in LangGraph test. They are skips by
design, not failures.

### 4.4 Why the transport tests matter

The simulator is deterministic and proves the mapping contract. The transport tests prove the
part the simulator cannot: that a `429` is retried, that a `4xx` is not, that the credential
never reaches the audit table, and that a failed call leaves a `mode: live` row with the HTTP
status. Those are the behaviours that decide whether an integration is trustworthy.

---

## 5. Live UAT

### 5.1 Harness

`scripts/qa_uat.py` drives the real HTTP API: it signs in, creates probe prospects, exercises
each workflow and prints a pass/fail line per workflow. It runs against a running server on an
isolated SQLite file with the deterministic heuristic engine.

### 5.2 Module 5 workflows

| Workflow | Verified behaviour |
|---|---|
| UAT-22 | Salesforce and HubSpot field maps present; unknown provider returns `422 invalid_provider` |
| UAT-23 | `sync_contact` to contact, `activity_log` to activity, `update_stage` to deal; all `mode: simulated`; audit rows carry the right `entity_type` |
| UAT-24 | Unknown operation returns `422 invalid_operation`; sync-log count unchanged |
| UAT-25 | Stored interaction carries id, lead, type, date, summary, key points and action items |
| UAT-17 | Failed sync leaves the lead and its stored interaction intact |

### 5.3 Why UAT runs over HTTP

The API tests import the application and call it in-process. The UAT signs in, obtains a token
and sends real requests. That catches the class of defect the in-process tests miss: a route
mounted under the wrong prefix, a dependency that only fails under a real request, or a response
shape the UI cannot consume.

---

## 6. UI verification

### 6.1 Contract test

`tests/test_frontend_compat.py` asserts that every CRM and conversation route the page calls
resolves through `frontend/api_compat.py` to the canonical API. A route rename fails the test
before it reaches a browser.

### 6.2 Headless render

`scripts/qa_conversations_render.py` runs the page with Streamlit's `AppTest`, creates a probe
prospect with one stored summary and three simulated syncs, and asserts that all seven expected
sections reach the rendered element tree:

| Expected section | Present |
|---|---|
| New summary | yes |
| Latest summary | yes |
| CRM sync status | yes |
| Run a sync | yes |
| Field mapping | yes |
| Recent activity | yes |
| History | yes |

### 6.3 Browser walkthrough

On 18 November 2026 the page was opened in a real browser against a running API and Streamlit
server with stored data:

| Check | Result |
|---|---|
| Every section rendered | yes |
| Stored summary visible | yes |
| Three CRM sync rows visible (`contact`, `activity`, `deal`) | yes |
| Simulated-transport label present | yes |
| Console errors | 0 |
| Horizontal overflow | none (`scrollWidth` = `clientWidth`) |

Evidence: `docs/qa/evidence/2026-11-18-browser-walkthrough.md`.

### 6.4 Why three layers for one page

The contract test proves the page can reach the API. The render test proves the page receives and
places every field. The browser walkthrough proves the result is usable in a browser. Each can
fail while the others pass, so all three are kept.

---

## 7. AI honesty testing

### 7.1 Grounding tests

The summariser is tested for what it must not do: it may not invent an action item, a key point or
a sentiment that the transcript does not contain. The test supplies a transcript with one explicit
commitment and asserts that the returned list contains exactly that commitment.

### 7.2 Live provider gate

`scripts/check_ai_integration.py` exercises six operations against the configured provider and
reports whether a mock was used:

| Signal | Result |
|---|---|
| Operations | **6/6 passed** |
| `used_mock` | `false` |
| Date | 17 November 2026 |

### 7.3 Why both

A mock proves the contract and the fallback. A live gate proves the real provider path and the
response parsing. Reporting them separately prevents the common error of presenting a mock run as
a live model call.

---

## 8. Defect management

### 8.1 Log

| Signal | Result |
|---|---|
| Defects logged | **20** |
| Closed | 18 |
| Open | 2 (`BUG-011`, `BUG-020`), both Low |

Each entry in `docs/qa/bug-log.md` records severity, reproduction steps, expected and actual
behaviour, and the fix or the reason it remains open.

### 8.2 Severity policy

| Severity | Meaning | Handling |
|---|---|---|
| Critical | Data loss, auth bypass, or the product cannot start | Blocks the milestone |
| High | A core workflow fails | Fixed before sign-off |
| Medium | A workflow works with a workaround | Scheduled and disclosed |
| Low | Cosmetic or test-only | Logged, disclosed, may remain open |

Both open defects are Low and are disclosed rather than hidden. `BUG-020` is a defect in a
contributor's own test suite, not in the product, and is recorded as such.

---

## 9. Verification and proof

### 9.1 Results

| Check | Result |
|---|---|
| Test cases | **81** |
| Module 5 cases | **15 passed** |
| Live UAT workflows | **25 passed, 0 partial, 0 failed** |
| Full suite, SQLite | **191 passed, 7 skipped** |
| Full suite, PostgreSQL 16 | **177 passed, 0 skipped** |
| CRM live-transport tests | **16 passed** |
| Headless render | **7 sections, no exception** |
| Browser walkthrough | **every section, 0 console errors, no overflow** |
| Live AI gate | **6/6, `used_mock=false`** |
| Defects open | 2, both Low |

### 9.2 Reproduction commands

```powershell
# Full suite on SQLite
$env:JWT_SECRET = "test-secret-value-0123456789"
python -m pytest -q

# Module 5 focus
python -m pytest tests/test_api_ai.py tests/test_frontend_compat.py -k "crm or conversation" -q

# CRM live transport
python -m pytest tests/test_crm_transport.py -q

# Live UAT against a running server
python scripts/qa_uat.py

# Headless Conversations render
python scripts/qa_conversations_render.py

# Live AI gate
python scripts/check_ai_integration.py
```

### 9.3 Evidence files

| Artefact | Path |
|---|---|
| Module 5 test report | `docs/qa/milestone3-test-report.md` |
| Full role report | `docs/reports/Milestone 3 report - QA.md` |
| Test cases | `docs/qa/test-cases.md` |
| Test scenarios | `docs/qa/test-scenarios.md` |
| Traceability matrix | `docs/qa/traceability-matrix.md` |
| Defect log | `docs/qa/bug-log.md` |
| Regression procedure | `docs/qa/regression-suite.md` |
| SQLite suite | `docs/qa/evidence/2026-11-17-pytest-sqlite.txt` |
| Module 5 focused run | `docs/qa/evidence/2026-11-17-pytest-module5-focused.txt` |
| CRM transport tests | `docs/qa/evidence/2026-11-18-pytest-crm-transport.txt` |
| Live UAT | `docs/qa/evidence/2026-11-17-uat-live-milestone3.md` |
| Headless render | `docs/qa/evidence/2026-11-17-conversations-headless-render.txt` |
| Browser walkthrough | `docs/qa/evidence/2026-11-18-browser-walkthrough.md` |
| Live AI gate | `docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt` |
| PostgreSQL suite | `docs/qa/evidence/2026-11-06-pytest-postgres.txt` |

---

## 10. Milestone 3 deliverable checklist

| Deliverable | Implementation | Proof |
|---|---|---|
| Test cases for Module 5 | `docs/qa/test-cases.md`, 15 cases | Test case table |
| Test scenarios | `docs/qa/test-scenarios.md`, 35 scenarios | Scenario table |
| Requirement traceability | `docs/qa/traceability-matrix.md` | FR and AC rows |
| Automated coverage | `tests/test_api_ai.py`, `tests/test_frontend_compat.py`, `tests/test_crm_transport.py` | Focused run and full suite |
| Live UAT | `scripts/qa_uat.py`, 25 workflows | UAT evidence |
| UI contract and render | `scripts/qa_conversations_render.py`, contract tests | Render evidence |
| Browser walkthrough | Manual session, 18 November 2026 | Walkthrough evidence |
| AI honesty tests | Grounding tests and live gate | Gate evidence |
| Defect log | `docs/qa/bug-log.md`, 20 entries | Bug log |
| Regression procedure | `docs/qa/regression-suite.md` | Documented commands and baseline record |
| CI workflow | `.github/workflows/ci.yml` | Workflow file |
