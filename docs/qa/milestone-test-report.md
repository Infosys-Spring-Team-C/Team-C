# Milestone Test Report

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Report date:** 27 October 2026
**Prepared by:** Mohamed Isharak M - QA / Test Engineer and Project Lead
**Repository:** `Infosys-Spring-Team-C/Team-C`
**Commit under test:** `fix/open-defects` on top of `main` at `46663fe` (the frontend
integration merge). `main` merged `feature/ai-integration` at `1f3fc11` (AI package and
integration fixes) and `feature/frontend-integration` at `46663fe` (Maheksaba's UI plus the
lead's adapter). That line sits on merge commit `fbe1fbc` (`origin/team_c_sai` into
`feature/backend-integration`) and its reconciliation commit.
**Milestone:** M2 evaluation (Modules 3 and 4 demonstrated, Modules 1-6 integrated)

---

## 1. Executive summary

The integrated backend, database, AI layer and Streamlit frontend are **functionally
verified and safe to demonstrate**. **156 automated tests pass against PostgreSQL 16.15**
and **150 pass on SQLite** (6 PostgreSQL-only tests skipped). The external AI engine returns
validated output for **all six operations** with the mock provider. The frontend's adapter
passed **12/12 live checks** against the containerised API with authentication enabled, the
Streamlit script executes with **0 exceptions** under `AppTest`, and the UI was loaded in a
browser and exercised through a real scoring call.

The Docker stack was built and started on this machine: `db`, `api` and `frontend` all
reported **healthy**, the API applied the Alembic migration to PostgreSQL, and
`/api/v1/health` returned `status: ok`. This closes the last High defect (BUG-012).

There are **no failures**. One Low defect remains open by explicit scope decision:
follow-ups cannot be dismissed (BUG-011). It does not affect FR-052, which requires the
panel, not dismissal.

The application is verified for a **local demonstration**, not for a production
deployment: it has no TLS termination, no real e-mail or CRM provider, and the AI package
was exercised with its mock provider only.

The most important quality property of this build is that it **does not overstate itself**:
uncalibrated probabilities are withheld, undefined KPIs are returned as `null`, unavailable
integrations return `501` with a reason, and the UI no longer displays an invented accuracy
figure (BUG-015).

---

## 2. What was tested

| Layer | Coverage | Result |
|---|---|---|
| Unit - validators, security, services, AI engine | unit and contract tests | PASS |
| API - every documented endpoint | the full API suite | PASS |
| Database - schema, keys, constraints, migrations, dialect parity | SQLite + PostgreSQL 16.15 | PASS |
| Database workspace - generated DDL and ER diagram cannot drift | 5 drift tests + parity check | PASS |
| Integration - API↔DB, API↔AI, adapter contract | Live server + the merged `ai.*` package (mock provider) | PASS - gate 6/6 |
| AI quality - determinism, grounding, boundaries | 13 adversarial cases | PASS |
| UAT - 21 user workflows | Live HTTP on PostgreSQL | 20 PASS, 1 PARTIAL (blocker now fixed) |
| Regression | Full suite before and after each change | PASS |
| Deployment - Docker build and Compose | Docker 29.7.2, PostgreSQL 16, API, Streamlit | PASS - all three services healthy |
| Frontend - Streamlit integration | Adapter tests, 12/12 live gate, AppTest, browser check | PASS - human usability acceptance pending |

---

## 3. Results

### 3.1 Automated tests

| Environment | Command | Result |
|---|---|---|
| PostgreSQL 16.15 (final) | `pytest -q` with `TEST_DATABASE_URL` | **156 passed** in 84.55 s |
| SQLite (final) | `pytest -q` | **150 passed, 6 skipped** in 95.89 s |
| SQLite (after AI + frontend merge) | `pytest -q` | 148 passed, 6 skipped in 59.22 s |
| SQLite (after AI merge, before frontend) | `pytest -q` | 131 passed, 6 skipped in 60.46 s |
| SQLite (pre-AI baseline) | `pytest -q` | 116 passed, 6 skipped in 94.20 s |
| PostgreSQL 16.15 (pre-AI baseline) | `pytest -q` with `TEST_DATABASE_URL` | 122 passed in 88.26 s |

The 6 skips are the PostgreSQL-only module, which runs in the PostgreSQL command. The final
run adds the FR-032 channel assertions and the frontend accuracy-integrity test to the
148-test frontend merge baseline. One warning remains: a JWT key-length warning from a test
that deliberately uses a short key. The earlier `StarletteDeprecationWarning` is gone
(BUG-013).

### 3.2 Live user acceptance

| Metric | Value |
|---|---|
| Workflows | 21 |
| Passed | 20 |
| Partial | 1 (UAT-15) |
| Failed | 0 |

UAT-15's blocker was BUG-006 (no recommendation channel). The contract now carries
`suggested_channel`, and `test_recommendation_endpoint` asserts timing, channel and draft
together, so the API-level defect is fixed and verified. The 21-workflow live UAT was
**not** re-run after the AI and frontend merges; it still describes the pre-AI backend plus
the targeted re-verification above.

The frontend was verified separately by `scripts/check_frontend_integration.py` (12/12), a
headless `AppTest` run (0 exceptions) and a browser check of the scoring path. None of these
is a substitute for human acceptance of the eight UI requirements.

### 3.3 Requirement coverage

The last full requirement audit was performed before the frontend merge: **33 FRs PASS,
6 PARTIAL, 13 BLOCKED, 1 NOT RUN; 18 ACs PASS, 8 PARTIAL, 4 BLOCKED**. Since then three
verdicts changed: FR-032 and AC-019 (BUG-006 fixed and asserted) and FR-033 (score and
recommendation observed in the browser).

| Verdict | FRs (53) | ACs (30) | Note |
|---|---|---|---|
| PASS | 35 | 19 | FR-032, FR-033 and AC-019 added |
| PARTIAL | 5 | 7 | unchanged from the pre-frontend audit |
| BLOCKED | 12 | 4 | unchanged; frontend requirements are implemented but not formally re-scored |
| NOT RUN | 1 | 0 | FR-021 refresh-variant behaviour |
| FAIL | 0 | 0 | |

The frontend requirements are no longer blocked in the code: the screens exist, the adapter
translates every call, and the live gate passes. They are **not** claimed as formally
accepted because no human acceptance pass has been recorded.

### 3.4 Defects

| Severity | Open | Closed |
|---|---|---|
| Critical | 0 | 2 |
| High | 0 | 8 |
| Medium | 0 | 2 |
| Low | 1 (BUG-011) | 2 |
| **Total** | **1** | **14** |

**BUG-012** (Docker never executed) is closed: both images built, all three Compose services
became healthy, and the API migrated PostgreSQL. **BUG-006** (recommendation channel) is
closed with contract and endpoint tests. **BUG-013** (Starlette deprecation warning) is
closed by adding `httpx2` to the development requirements. **BUG-015** (a hard-coded
"Scoring Accuracy 98.4%" in the UI) was found during the browser check and closed by
replacing the card with the engine name reported by `/health`.

The two database defects found during review, **BUG-009** (ER description contradicted the
SQL) and **BUG-010** (`VARCHAR(15)` phone column), remain closed by the merge reconciliation:
the workspace artefacts are generated from `backend/db.py` and a test fails on drift.

**BUG-008** (`ai.*` absent) and **BUG-014** (frontend adapter mis-read the saved-analysis
endpoint) are closed by their respective merges. BUG-014 is notable because the first smoke
check reported a false pass; the check was tightened before the defect was closed.

---

## 4. What works, demonstrably

Each item below was observed in a live run, not inferred:

1. **Authentication and RBAC.** Token issue, `/me`, viewer read-only, admin-only user
   administration, rejection of expired and wrongly-signed tokens. The Docker stack ran with
   `AUTH_ENABLED=true` and a user created through `backend.cli`.
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
7. **Recommendations.** Next-best-action with timing, channel and content strategy
   (FR-032). The channel is `email` when outreach is justified and `null` when it is not.
8. **Conversations.** Transcript summarised into a summary, four discussion points and one
   action item, stored as a sales interaction.
9. **CRM failure path.** `501`, a failure row in the sync log, local data intact.
10. **Analytics.** Conversion rate computed; three undefined KPIs withheld with
    `pending_definition: true`.
11. **Database.** Eight tables, six foreign keys, cascade and `SET NULL` behaviour, unique
    e-mail key, JSON/JSONB round-trip, and a migration that upgrades **and downgrades**
    cleanly on PostgreSQL. The portable baseline in the database workspace was applied to a
    second empty database and produced the identical 110 columns, 6 foreign keys and 31
    indexes.
12. **Frontend.** The Streamlit UI loads against the containerised API, reports
    "Backend Active", computes a score, shows `n/a` with "No calibrated model configured",
    and displays the recommendation. Its adapter passed 12/12 live checks.
13. **Deployment.** `docker compose build` and `docker compose up -d` bring up PostgreSQL,
    the API and the frontend; all three health checks pass and the migration runs
    automatically.

---

## 5. What does not work, or was not verified

This section is the reason the report is trustworthy.

| # | Limitation | Why | Consequence |
|---|---|---|---|
| 1 | No human usability acceptance of the UI | The browser check was scripted and covered the scoring path, not every screen | The 8 UI requirements are implemented and exercised but not formally signed off |
| 2 | E-mail send does not exist | Provider unconfirmed (D-05) | Returns `501`; the UI surfaces that message instead of faking a send |
| 3 | CRM synchronisation does not execute | Credentials unconfirmed (D-06) | Returns `501` and logs the attempt |
| 4 | Real model calls unverified | No OpenAI/Gemini key used | The merged `ai.*` package passes its 6/6 gate with the **mock** provider only |
| 5 | Docker verified locally only | No production orchestrator, TLS or secrets manager | The Compose stack is proven on one machine; production hardening is out of scope |
| 6 | No scoring accuracy figure | Metric and dataset undefined (D-13) | No accuracy percentage is claimed; the UI shows the engine name instead |
| 7 | No performance figure | Measurement conditions undefined (D-11) | No latency compliance is claimed |
| 8 | No UAT satisfaction score | Survey undefined (D-12) | No satisfaction percentage is claimed |
| 9 | Database-workspace Compose file unexecuted | Only the root Compose stack was started | The SQL and migration paths are verified; that separate container entrypoint is not |
| 10 | Restart persistence not replayed | Not automated | `FR-009` and `AC-001` are `PARTIAL` |
| 11 | Refresh-variant behaviour not asserted | No test compares two generated drafts | `FR-021` is `NOT RUN` |
| 12 | Follow-ups are read-only | No dismissal endpoint (BUG-011) | FR-052 is satisfied; clearing a follow-up is not supported |

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
  reintroduces a fabricated probability, a fake zero KPI or an invented accuracy percentage
  will fail the suite.
* The deployment path is no longer theoretical: the same Compose file a reviewer would use
  was built and started here.

**Weaknesses**

* The frontend contract and rendering are tested, but no person has yet judged the screens
  for usability or visual defects.
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
| A reviewer asks to see the UI | Medium | Low | Run the Compose stack and open `http://127.0.0.1:8501`; state that human acceptance is pending |
| A reviewer asks for an accuracy figure | High | Medium | Explain D-13 and show the honest `null` probability and the `n/a` card |
| A reviewer asks to see Docker | Medium | Low | `docker compose up --build -d`, then `/api/v1/health` and the Streamlit health endpoint |
| A future schema change leaves the generated workspace artefacts stale | Medium | Medium | `scripts/render_db_workspace.py --check` runs inside the suite, so the build fails instead of drifting |
| The AI package lands and the adapter fails | Low | Medium | Run `scripts/check_ai_integration.py` before merging; it must print `6/6` |
| A dependency upgrade removes `use_container_width` | Medium | Low | The frontend pins Streamlit 1.65; the migration is recorded as a maintenance item |

---

## 8. Evidence index

| Artifact | Path |
|---|---|
| Environment and versions | [`evidence/2026-10-26-environment.txt`](evidence/2026-10-26-environment.txt) |
| Pytest, SQLite | [`evidence/2026-10-26-pytest-sqlite.txt`](evidence/2026-10-26-pytest-sqlite.txt) |
| Pytest, SQLite (post-merge) | [`evidence/2026-10-26-pytest-sqlite-postmerge.txt`](evidence/2026-10-26-pytest-sqlite-postmerge.txt) |
| Pytest, SQLite (after frontend merge, 148 passed) | [`evidence/2026-10-27-pytest-sqlite-frontend.txt`](evidence/2026-10-27-pytest-sqlite-frontend.txt) |
| Pytest, SQLite (final, 150 passed) | [`evidence/2026-10-27-pytest-sqlite-final.txt`](evidence/2026-10-27-pytest-sqlite-final.txt) |
| Pytest, PostgreSQL | [`evidence/2026-10-26-pytest-postgres.txt`](evidence/2026-10-26-pytest-postgres.txt) |
| Pytest, PostgreSQL (post-merge) | [`evidence/2026-10-26-pytest-postgres-postmerge.txt`](evidence/2026-10-26-pytest-postgres-postmerge.txt) |
| Pytest, PostgreSQL (final, 156 passed) | [`evidence/2026-10-27-pytest-postgres-open-defects.txt`](evidence/2026-10-27-pytest-postgres-open-defects.txt) |
| Schema parity, generated DDL vs Alembic | [`evidence/2026-10-26-schema-parity.txt`](evidence/2026-10-26-schema-parity.txt) |
| Live UAT, readable | [`evidence/2026-10-26-uat-live-postgres-heuristic.md`](evidence/2026-10-26-uat-live-postgres-heuristic.md) |
| Live UAT, machine-readable | [`evidence/2026-10-26-uat-live-postgres-heuristic.json`](evidence/2026-10-26-uat-live-postgres-heuristic.json) |
| Live UAT, post-merge | [`evidence/2026-10-26-uat-live-postmerge.md`](evidence/2026-10-26-uat-live-postmerge.md), [`evidence/2026-10-26-uat-live-postmerge.json`](evidence/2026-10-26-uat-live-postmerge.json) |
| AI integration gate, external engine + mock provider | [`evidence/2026-10-27-ai-integration-gate.txt`](evidence/2026-10-27-ai-integration-gate.txt) |
| Frontend integration gate, live API | [`evidence/2026-10-27-frontend-integration-gate.txt`](evidence/2026-10-27-frontend-integration-gate.txt) |
| Streamlit app execution (AppTest) | [`evidence/2026-10-27-frontend-apptest.txt`](evidence/2026-10-27-frontend-apptest.txt) |
| Docker Compose stack, build + health + gate | [`evidence/2026-10-27-docker-compose-verification.txt`](evidence/2026-10-27-docker-compose-verification.txt) |
| Browser check of the containerised UI | [`evidence/2026-10-27-browser-ui-check.txt`](evidence/2026-10-27-browser-ui-check.txt) |
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

**Recommendation: proceed to the milestone demonstration for the backend, database, AI and
frontend layers, with the limitations in section 5 stated openly.**

Conditions:

1. Demonstrate the UI from the Compose stack, but do not claim formal usability acceptance;
   no human acceptance pass has been recorded.
2. Do not claim a scoring accuracy figure, because no metric or dataset exists. The UI now
   shows the engine name instead of a percentage.
3. Do not claim a production deployment. The local Compose stack is verified; TLS, secrets
   management and external providers are not.
4. Run the full suite and the 21-workflow live UAT again after any further merge, and update
   this report.
5. Keep BUG-011 recorded as an accepted limitation unless follow-up dismissal becomes a
   requirement.

---

## 10. Sign-off

| Role | Name | Status |
|---|---|---|
| QA / Test Engineer | Mohamed Isharak M | Signed - 27 October 2026 |
| Project Lead | Mohamed Isharak M | Signed - 27 October 2026 |
| Backend owner | M Doran | Pending |
| Database owner | Marri Sai Surekha | Merge verified by the lead - owner sign-off pending |
| AI owner | Mahidhar Reddy | Package merged - owner sign-off pending |
| Frontend owner | Maheksaba Akbar Shaikh | UI merged and verified by the lead - owner sign-off pending |
