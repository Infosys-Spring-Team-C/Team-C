# Milestone Test Report

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Report date:** 27 October 2026
**Prepared by:** Mohamed Isharak M - QA / Test Engineer and Project Lead
**Repository:** `Infosys-Spring-Team-C/Team-C`
**Commit under test:** `feature/frontend-integration` at `92c9c6c` (the frontend adapter and
packaging on top of `3cc616d`, Maheksaba's UI as submitted), branched from `main` at
`1f3fc11`, which merged `feature/ai-integration` at `3864e86` (the AI package and its
integration fixes). That line sits on merge commit `fbe1fbc` (`origin/team_c_sai` into
`feature/backend-integration`) and its reconciliation commit.
**Milestone:** M2 evaluation (Modules 3 and 4 demonstrated, Modules 1-6 integrated)

---

## 1. Executive summary

The integrated backend, database and AI layer are **functionally verified and safe to
demonstrate**. After the AI package and the Streamlit frontend were merged, **148 automated
tests pass on SQLite** (6 skipped, all optional-dependency skips). The external AI engine
returns validated output for **all six operations** with the mock provider, and the
frontend's adapter passed **12/12 live checks** with the Streamlit script executing with
**0 exceptions**. The earlier **122-test PostgreSQL 16** run still stands for the pre-AI
commit; it was **not** re-run after the AI or frontend merges because the local cluster would
not stay up, so PostgreSQL coverage of those changes is unverified.

There is **one partial acceptance result** - the next-best-action recommendation has no
channel field (FR-032, BUG-006) - and **no failures**.

The application is **not** claimed to be deployment-ready: the Docker stack was never
started because no daemon was available, and the Streamlit frontend was merged after this
test run, so its eight user-facing requirements still need acceptance testing.

The most important quality property of this build is that it **does not overstate itself**:
uncalibrated probabilities are withheld, undefined KPIs are returned as `null`, and
unavailable integrations return `501` with a reason instead of pretending to work.

---

## 2. What was tested

| Layer | Coverage | Result |
|---|---|---|
| Unit - validators, security, services, AI engine | 108 test functions across 8 files | PASS |
| API - every documented endpoint | 122 collected tests | PASS |
| Database - schema, keys, constraints, migrations, dialect parity | SQLite + PostgreSQL 16 | PASS |
| Database workspace - generated DDL and ER diagram cannot drift | 5 drift tests + parity check | PASS |
| Integration - API↔DB, API↔AI, adapter contract | Live server + the merged `ai.*` package (mock provider) | PASS - gate 6/6, BUG-008 closed |
| AI quality - determinism, grounding, boundaries | 13 adversarial cases | PASS |
| UAT - 21 user workflows | Live HTTP on PostgreSQL | 20 PASS, 1 PARTIAL |
| Regression | Full suite before and after each change | PASS |
| Deployment | Docker build and Compose | **BLOCKED** (BUG-012) |
| Frontend | Streamlit integration | **BLOCKED** (not delivered) |

---

## 3. Results

### 3.1 Automated tests

| Environment | Command | Result |
|---|---|---|
| SQLite (after AI + frontend merge) | `pytest -q` | **148 passed, 6 skipped** in 59.22 s |
| SQLite (after AI merge, before frontend) | `pytest -q` | **131 passed, 6 skipped** in 60.46 s |
| SQLite (pre-AI baseline) | `pytest -q` | 116 passed, 6 skipped in 94.20 s |
| PostgreSQL 16.15 (pre-AI baseline) | `pytest -q` with `TEST_DATABASE_URL` | 122 passed in 88.26 s |

The 6 skips are the PostgreSQL-only module, which runs in the second command. The 17 new
tests are the frontend adapter suite (`tests/test_frontend_compat.py`). The PostgreSQL run
was **not** repeated after the AI or frontend merges: the local cluster would not stay up.

### 3.2 Live user acceptance

| Metric | Value |
|---|---|
| Workflows | 21 |
| Passed | 20 |
| Partial | 1 (UAT-15 → BUG-006) |
| Failed | 0 |

This UAT run predates the AI and frontend merges and was **not** repeated afterwards. It
therefore describes the pre-AI backend. The frontend was verified separately by
`scripts/check_frontend_integration.py` (12/12) and a headless `AppTest` run (0 exceptions);
neither is a substitute for human acceptance of the eight UI requirements.

### 3.3 Requirement coverage

| Verdict | FRs (53) | ACs (30) |
|---|---|---|
| PASS | 33 | 18 |
| PARTIAL | 6 | 8 |
| BLOCKED | 13 | 4 |
| NOT RUN | 1 | 0 |
| FAIL | 0 | 0 |

### 3.4 Defects

| Severity | Open | Closed |
|---|---|---|
| Critical | 0 | 2 |
| High | 1 (BUG-012, environment) | 6 |
| Medium | 1 | 1 |
| Low | 2 | 1 |
| **Total** | **4** | **10** |

The open High defect is **BUG-012** (Docker was never executed). It is not a defect in the
delivered code; it is a blocker on verification, and it now also covers the frontend image.

The two database defects found during review, **BUG-009** (ER description contradicted the
SQL) and **BUG-010** (`VARCHAR(15)` phone column), are closed by the merge reconciliation:
the workspace artefacts are now generated from `backend/db.py` and a test fails on drift.

**BUG-008** (`ai.*` absent) and **BUG-014** (frontend adapter mis-read the saved-analysis
endpoint) are closed by their respective merges. BUG-014 is notable because the first smoke
check reported a false pass; the check was tightened before the defect was closed.

---

## 4. What works, demonstrably

Each item below was observed in a live run, not inferred:

1. **Authentication and RBAC.** Token issue, `/me`, viewer read-only, admin-only user
   administration, rejection of expired and wrongly-signed tokens.
2. **Prospect management.** Create, read, search, paginate, update, delete; seven lifecycle
   stages; duplicate detection by e-mail and by company+contact.
3. **CSV import.** Two rows imported, one duplicate reported with the row number and the
   reason, valid rows stored despite the bad row.
4. **Lead intelligence.** Business needs, opportunities, industry context, qualification and
   missing-information reporting, persisted against the lead.
5. **Outreach.** Generation from the six SRS inputs, editing, campaign storage and history.
   Send refuses visibly with `501`.
6. **Scoring.** 0-100 explainable score with four factors whose points sum to the score;
   append-only history; `conversion_probability` correctly `null`.
7. **Conversations.** Transcript summarised into a summary, four discussion points and one
   action item, stored as a sales interaction.
8. **CRM failure path.** `501`, a failure row in the sync log, local data intact.
9. **Analytics.** Conversion rate computed; three undefined KPIs withheld with
   `pending_definition: true`.
10. **Database.** Eight tables, six foreign keys, cascade and `SET NULL` behaviour, unique
    e-mail key, JSON/JSONB round-trip, and a migration that upgrades **and downgrades**
    cleanly on PostgreSQL. The portable baseline in the database workspace was applied to a
    second empty database and produced the identical 110 columns, 6 foreign keys and 31
    indexes.

---

## 5. What does not work, or was not verified

This section is the reason the report is trustworthy.

| # | Limitation | Why | Consequence |
|---|---|---|---|
| 1 | Frontend not browser-tested | Merged from Maheksaba's branch, but no human click-through was recorded | Adapter is unit-tested (17) and passed 12/12 live checks; AppTest executed the script with 0 exceptions. The 8 UI requirements still need human acceptance |
| 2 | E-mail send does not exist | Provider unconfirmed (D-05) | Returns `501`; the UI surfaces that message instead of faking a send |
| 3 | CRM synchronisation does not execute | Credentials unconfirmed (D-06) | Returns `501` and logs the attempt |
| 4 | Real model calls unverified | No OpenAI/Gemini key used | The merged `ai.*` package passes its 6/6 gate with the **mock** provider only |
| 5 | Docker never started | No daemon on the test machine (BUG-012) | Deployment is unverified, including the new frontend image |
| 6 | No scoring accuracy figure | Metric and dataset undefined (D-13) | No accuracy percentage is claimed |
| 7 | No performance figure | Measurement conditions undefined (D-11) | No latency compliance is claimed |
| 8 | No UAT satisfaction score | Survey undefined (D-12) | No satisfaction percentage is claimed |
| 9 | Database workspace Compose file unexecuted | No daemon on the test machine (BUG-012) | The SQL and migration paths are verified; the container entrypoint is not |
| 10 | Restart persistence not replayed | Not automated | `FR-009` and `AC-001` are `PARTIAL` |
| 11 | Refresh-variant behaviour not asserted | No test compares two generated drafts | `FR-021` is `NOT RUN` |
| 12 | Recommendation has no channel | Contract gap | `FR-032` is `PARTIAL` (BUG-006) |

---

## 6. Quality observations

**Strengths**

* The suite is deterministic and self-contained: every test builds its own data and rolls
  back. There are no ordering dependencies and no shared fixtures that leak state.
* Both database dialects are exercised. Dialect-specific behaviour (JSONB, `SET NULL`) is
  tested explicitly rather than assumed.
* Failure paths are tested as seriously as happy paths: invalid AI output, provider
  absence, duplicate imports, expired tokens, failed CRM sync.
* The system's honesty rules are enforced by tests, not by convention. A future change that
  reintroduces a fabricated probability or a fake zero KPI will fail the suite.

**Weaknesses**

* The frontend is a blind spot. The contract is tested but nothing consumes it.
* The external AI integration is tested against a stub, which proves the adapter's
  translation logic but not the real package's behaviour.
* No performance or load testing exists. The UAT timings in the evidence file are
  observations, not a benchmark.
* Coverage is behavioural, not line-based. No coverage percentage is reported because none
  was measured.

---

## 7. Risk assessment for the milestone demonstration

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A reviewer asks to see the UI | High | High | Demonstrate the API through `/docs` and the Postman collection; state plainly that the UI is pending |
| A reviewer asks for an accuracy figure | High | Medium | Explain D-13 and show the honest `null` probability design |
| A reviewer asks to see Docker | Medium | High | State that it is unverified and why; do not claim otherwise |
| A future schema change leaves the generated workspace artefacts stale | Medium | Medium | `scripts/render_db_workspace.py --check` runs inside the suite, so the build fails instead of drifting |
| The AI package lands and the adapter fails | Medium | Medium | Run `scripts/check_ai_integration.py` before merging; it must print `6/6` |

---

## 8. Evidence index

| Artifact | Path |
|---|---|
| Environment and versions | [`evidence/2026-10-26-environment.txt`](evidence/2026-10-26-environment.txt) |
| Pytest, SQLite | [`evidence/2026-10-26-pytest-sqlite.txt`](evidence/2026-10-26-pytest-sqlite.txt) |
| Pytest, SQLite (post-merge) | [`evidence/2026-10-26-pytest-sqlite-postmerge.txt`](evidence/2026-10-26-pytest-sqlite-postmerge.txt) |
| Pytest, SQLite (after frontend merge, 148 passed) | [`evidence/2026-10-27-pytest-sqlite-frontend.txt`](evidence/2026-10-27-pytest-sqlite-frontend.txt) |
| Pytest, PostgreSQL | [`evidence/2026-10-26-pytest-postgres.txt`](evidence/2026-10-26-pytest-postgres.txt) |
| Pytest, PostgreSQL (post-merge) | [`evidence/2026-10-26-pytest-postgres-postmerge.txt`](evidence/2026-10-26-pytest-postgres-postmerge.txt) |
| Schema parity, generated DDL vs Alembic | [`evidence/2026-10-26-schema-parity.txt`](evidence/2026-10-26-schema-parity.txt) |
| Live UAT, readable | [`evidence/2026-10-26-uat-live-postgres-heuristic.md`](evidence/2026-10-26-uat-live-postgres-heuristic.md) |
| Live UAT, machine-readable | [`evidence/2026-10-26-uat-live-postgres-heuristic.json`](evidence/2026-10-26-uat-live-postgres-heuristic.json) |
| Live UAT, post-merge | [`evidence/2026-10-26-uat-live-postmerge.md`](evidence/2026-10-26-uat-live-postmerge.md), [`evidence/2026-10-26-uat-live-postmerge.json`](evidence/2026-10-26-uat-live-postmerge.json) |
| AI integration gate, external engine + mock provider | [`evidence/2026-10-27-ai-integration-gate.txt`](evidence/2026-10-27-ai-integration-gate.txt) |
| Frontend integration gate, live API | [`evidence/2026-10-27-frontend-integration-gate.txt`](evidence/2026-10-27-frontend-integration-gate.txt) |
| Streamlit app execution (AppTest) | [`evidence/2026-10-27-frontend-apptest.txt`](evidence/2026-10-27-frontend-apptest.txt) |
| Test plan | [`test-plan.md`](test-plan.md) |
| Test cases | [`test-cases.md`](test-cases.md) |
| Traceability | [`traceability-matrix.md`](traceability-matrix.md) |
| API matrix | [`api-test-matrix.md`](api-test-matrix.md) |
| Database matrix | [`database-test-matrix.md`](database-test-matrix.md) |
| Integration plan | [`integration-test-plan.md`](integration-test-plan.md) |
| AI quality validation | [`ai-quality-validation.md`](ai-quality-validation.md) |
| Regression suite | [`regression-suite.md`](regression-suite.md) |
| Defect log | [`bug-log.md`](bug-log.md) |
| UAT plan and results | [`uat-plan.md`](uat-plan.md), [`uat-results.md`](uat-results.md) |

---

## 9. Recommendation

**Recommendation: proceed to the milestone demonstration for the backend, database and AI
layers, with the limitations in section 5 stated openly.**

Conditions:

1. Do not claim the frontend works, because it does not exist yet.
2. Do not claim a scoring accuracy figure, because no metric or dataset exists.
3. Do not claim deployment, because Docker was never executed.
4. The database merge is complete and re-tested; re-run the full suite and the live UAT
   again after the AI package merge, and update this report.
5. Fix BUG-006 (recommendation channel) before the final milestone; it is small and it is
   the only partial result.

---

## 10. Sign-off

| Role | Name | Status |
|---|---|---|
| QA / Test Engineer | Mohamed Isharak M | Signed - 26 October 2026 |
| Project Lead | Mohamed Isharak M | Signed - 26 October 2026 |
| Backend owner | M Doran | Pending |
| Database owner | Marri Sai Surekha | Merge verified by the lead - owner sign-off pending |
| AI owner | Mahidhar Reddy | Pending - package merge required |
| Frontend owner | Maheksaba Akbar Shaikh | Pending - UI required before UAT can complete |
