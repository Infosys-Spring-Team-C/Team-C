# Milestone Test Report

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Report date:** 5 November 2026
**Prepared by:** Mohamed Isharak M - QA / Test Engineer
**Repository:** `Infosys-Spring-Team-C/Team-C`
**Build under test:** `main` at `66c1255` plus the Milestone 2 consolidation commit of
5 November 2026 (the AI package, the CRM simulator, the rewritten Streamlit client and
the scoring/recommendation work merged into the canonical tree).
**Milestone:** M2 evaluation (Modules 3 and 4 demonstrated; Modules 1-6 integrated)

---

## 1. Executive summary

The integrated backend, database, AI layer and Streamlit frontend are **functionally
verified and safe to demonstrate**. **176 automated tests pass against PostgreSQL 16 with
no skips**, and **170 pass on SQLite with 6 expected skips** (the PostgreSQL-only module).
The AI integration gate returns **6/6 operations passed** through the merged `ai.*`
package, and the database workspace drift check reports **OK** for the SQL baseline and
the ER diagram.

Milestone 2 delivered its two modules end to end:

* **Module 3 - AI outreach generation.** Prompt inputs for tone, length, outreach type,
  goal, pain points and industry; draft generation and variation refresh; campaign
  storage; edit, copy, save and record-as-sent in the Outreach Studio.
* **Module 4 - Lead scoring and recommendations.** An explainable eight-factor score
  mapped onto the four SRS dimensions, append-only score history, a next-best-action
  recommendation with timing, channel and content strategy, and the Lead Score and
  Outreach Strategy panels in the UI.

There are **no test failures**. The single open defect is Low severity and an accepted
scope decision: follow-ups cannot be dismissed (BUG-011), while FR-052 requires the panel,
which works.

Two limits are stated openly and are not presented as achievements:

1. **No live model call is verified.** The engine ran the full workflow through the
   package's deterministic **mock** provider. A key present in the environment was
   rejected by the provider (`HTTP 401`). Every result is labelled `used_mock=true` and
   `ai_mode=offline-mock`, and the UI shows the same state.
2. **No scoring-accuracy percentage is claimed.** The 85% target from the plan requires a
   labelled outcome dataset and a calibrated model. Neither exists, so
   `conversion_probability` stays `null` with an explicitly uncalibrated band.

---

## 2. What was tested

| Layer | Coverage | Result |
|---|---|---|
| Unit - validators, security, services, AI engine | unit and contract tests | PASS |
| API - every documented endpoint | the full API suite | PASS |
| Database - schema, keys, constraints, migrations, dialect parity | SQLite + PostgreSQL 16 | PASS |
| Database workspace - generated DDL and ER diagram cannot drift | drift check + workspace tests | PASS |
| Integration - API to DB, API to AI, adapter contract | live server + merged `ai.*` package | PASS - gate 6/6 |
| AI quality - determinism, grounding, boundaries | adversarial cases | PASS |
| Outreach - six industries, prompt controls, regeneration | live HTTP on PostgreSQL | PASS |
| Scoring - boundedness, factor reconciliation, dimension mapping | unit + live HTTP | PASS |
| UAT - 21 user workflows | live HTTP on PostgreSQL (26 Oct) | 20 PASS, 1 PARTIAL (blocker since fixed) |
| Regression | full suite after each change | PASS |
| Deployment - Docker build and Compose | Docker, PostgreSQL 16, API, Streamlit | PASS - all three services healthy |
| Frontend - Streamlit integration | adapter tests + browser walkthrough | PASS - human acceptance pending |

---

## 3. Results

### 3.1 Automated tests

| Environment | Command | Result |
|---|---|---|
| PostgreSQL 16 (final) | `pytest -q` with `TEST_DATABASE_URL` | **176 passed, 0 skipped** in 93.80 s |
| SQLite (final) | `pytest -q` | **170 passed, 6 skipped** in 93.18 s |

The 6 skips are the PostgreSQL-only module, which runs in the PostgreSQL command. The
only warning is a JWT key-length warning from a test that deliberately uses a short key.

The count grew from the pre-merge baseline because this consolidation adds the
merge-integration module (auto engine selection, eight-to-four dimension aggregation, CRM
simulator, health metadata, rich demo seed) and the outreach greeting regression test.

### 3.2 AI integration gate

`python scripts/check_ai_integration.py` exercises every operation through the adapter:

```
PASS analyze_lead: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS generate_outreach: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS summarize_conversation: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS recommend: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS score_lead: engine=external provider=mock model=rule-based used_mock=False score=82 factors=8 probability=None
PASS interpret_analytics: engine=external provider=mock model=deterministic-demo-v1 used_mock=True

6/6 operations passed
```

### 3.3 Live user acceptance

| Metric | Value |
|---|---|
| Workflows | 21 |
| Passed | 20 |
| Partial | 1 (UAT-15) |
| Failed | 0 |

UAT-15's blocker was BUG-006 (no recommendation channel). The contract now carries
`suggested_channel`, and `test_recommendation_endpoint` asserts timing, channel and draft
together, so the API-level defect is fixed and verified. The full 21-workflow run was not
repeated after the frontend rewrite; the targeted re-verification above is the current
evidence.

### 3.4 Milestone 2 requirement verdicts

| Requirement | Verdict | Evidence |
|---|---|---|
| FR-019 personalized outreach generation | PASS | 6/6 live drafts across six industries |
| FR-020 tone, length, type, goal, pain points, industry inputs | PASS | adapter tests; drafts change with tone and length |
| FR-021 refresh/regenerate a new variant | PASS | `variant` rotation test; 6/6 bodies changed live |
| FR-022 edit a generated outreach | PASS | PATCH endpoint + browser edit/save |
| FR-023 copy outreach to clipboard | PASS | Outreach Studio copy panel |
| FR-024 send action | PARTIAL by design | returns `501` (SRS D-05); UI shows the refusal |
| FR-025 store outreach campaigns | PASS | `outreach_campaigns` rows on generate/save |
| FR-026 retrieve outreach history | PASS | draft history endpoint + UI reload |
| FR-027 generate/refresh/edit/copy/send in the UI | PASS | browser walkthrough |
| FR-028 produce a lead score | PASS | 0-100 score with eight factors |
| FR-029 conversion-probability estimate | PARTIAL by design | `null` + uncalibrated band; no calibrated model |
| FR-030 engagement, fit, intent, decision readiness | PASS | eight factors aggregated into the four dimensions |
| FR-031 store score history | PASS | append-only `lead_scores` |
| FR-032 timing, channel, content strategy | PASS | recommendation contract test + live calls |
| FR-033 display score and recommendation | PASS | Lead Score and Outreach Strategy panels |
| 85% scoring accuracy target | NOT MEASURED | no labelled dataset; see section 5 |

### 3.5 Defects

| Severity | Open | Closed |
|---|---|---|
| Critical | 0 | 2 |
| High | 0 | 9 |
| Medium | 0 | 3 |
| Low | 1 (BUG-011) | 3 |
| **Total** | **1** | **17** |

Closed in this Milestone 2 pass:

* **BUG-017** - titled contacts were greeted as `Hi Dr.,`. Fixed with an
  honorific-aware first-name helper in the AI package and the heuristic engine, covered
  by two regression tests.
* **BUG-018** - `auto` provider selection chose a keyed provider whose SDK was not
  installed, making the entire AI engine unavailable. `auto` now falls back to the
  labelled mock provider with an `ai_note`; an explicit provider still fails loudly.

Previously closed and re-verified: BUG-006 (recommendation channel), BUG-012 (Docker stack),
BUG-013 (Starlette warning), BUG-015 (fabricated accuracy card), BUG-016 (undeclared test
dependency).

---

## 4. What works, demonstrably

Each item below was observed in a live run, not inferred:

1. **Authentication and RBAC.** Token issue, `/me`, viewer read-only, admin-only user
   administration, rejection of expired and wrongly-signed tokens.
2. **Prospect management.** Create, read, search, paginate, update, delete; seven
   lifecycle stages; duplicate detection by e-mail and by company+contact.
3. **CSV import.** Valid rows stored, duplicates reported with row number and reason.
4. **Lead intelligence.** Business needs, opportunities, industry context, qualification
   and missing-information reporting, persisted against the lead.
5. **Outreach generation.** Six prompt controls forwarded to the AI package; channel, tone
   and length change the draft; regeneration rotates the rewritten section; drafts persist
   as campaigns; edit, copy, save and record-as-sent work; send refuses visibly with `501`.
6. **Scoring.** Bounded 0-100 score with eight explainable factors whose points reconcile
   to the score; append-only history; four SRS dimensions populated; `conversion_probability`
   correctly `null`.
7. **Recommendations.** Next-best-action with priority, timing, channel and content
   strategy; channel is present when outreach is justified and absent when it is not.
8. **Conversations.** Transcript summarised into a summary, discussion points and action
   items, stored as a sales interaction.
9. **CRM.** Provider-neutral payload mapping, labelled simulation, audit rows, status
   endpoint and sync history; no live transport is claimed.
10. **Analytics.** Conversion rate computed; undefined KPIs withheld with
    `pending_definition: true`.
11. **Database.** Eight tables, six foreign keys, cascade and `SET NULL` behaviour, unique
    e-mail key, JSON/JSONB round-trip, reversible migration, and a drift check that fails
    on divergence.
12. **Frontend.** Six workspaces, warm design system, login/logout, honest empty states,
    score and strategy panels, and a single API adapter; no console errors on the pages
    exercised.
13. **Deployment.** Compose brings up PostgreSQL, the API and the frontend; all three
    health checks pass and the migration runs automatically.

---

## 5. What does not work, or was not verified

| # | Limitation | Why | Consequence |
|---|---|---|---|
| 1 | No live OpenAI/Gemini call | The available key was rejected (`HTTP 401`) | All AI evidence uses the labelled mock provider |
| 2 | No scoring-accuracy figure | No labelled outcome dataset or calibrated model (D-13) | The 85% target is reported as a target, not an outcome |
| 3 | E-mail send does not exist | Provider unconfirmed (D-05) | Returns `501`; the UI surfaces that message |
| 4 | CRM transport does not execute | Credentials unconfirmed (D-06) | Labelled simulator + audit rows only |
| 5 | No human usability acceptance | Browser checks were scripted | The UI is exercised but not formally signed off |
| 6 | No performance figure | Measurement conditions undefined (D-11) | No latency compliance is claimed |
| 7 | No UAT satisfaction score | Survey undefined (D-12) | No satisfaction percentage is claimed |
| 8 | Follow-ups are read-only | No dismissal endpoint (BUG-011) | FR-052 is satisfied; clearing is not supported |
| 9 | Docker verified locally only | No orchestrator, TLS or secrets manager | Production hardening is out of scope |
| 10 | No CI workflow | Requires a decision on the target service | Tests are run manually with the documented commands |

---

## 6. Quality observations

**Strengths**

* The suite is deterministic and self-contained: every test builds its own data and rolls
  back. There are no ordering dependencies.
* Both database dialects are exercised. Dialect-specific behaviour is tested explicitly.
* Failure paths are tested as seriously as happy paths: invalid AI output, provider
  absence, duplicate imports, expired tokens, refused sends and failed CRM sync.
* The honesty rules are enforced by tests: a fabricated probability, a fake zero KPI or an
  invented accuracy percentage fails the suite.
* The deployment path is verified with the same Compose file a reviewer would use.

**Weaknesses**

* The frontend contract and rendering are tested, but no person has judged the screens for
  usability.
* The external AI integration is proven with the mock provider; live provider behaviour is
  untested.
* No performance or load testing exists.
* Coverage is behavioural, not line-based; no coverage percentage is reported.

---

## 7. Risk assessment for the milestone demonstration

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A reviewer asks to see the UI | Medium | Low | Run the Compose stack and open `http://127.0.0.1:8501` |
| A reviewer asks for an accuracy figure | High | Medium | Explain D-13; show the honest `null` probability and the `n/a` card |
| A reviewer asks whether a live model is used | High | Low | Show `ai_mode=offline-mock` and `used_mock`; state that no key was available |
| A reviewer asks to see Docker | Medium | Low | `docker compose up --build -d`, then the health endpoint |
| A schema change leaves workspace artefacts stale | Medium | Medium | The drift check runs in the suite and fails the build |
| A dependency upgrade breaks the UI | Medium | Low | Streamlit is pinned; migration is a recorded maintenance item |

---

## 8. Evidence index

| Artifact | Path |
|---|---|
| Pytest, PostgreSQL 16 (176 passed) | `docs/qa/evidence/2026-11-05-pytest-postgres.txt` |
| Pytest, SQLite (170 passed, 6 skipped) | `docs/qa/evidence/2026-11-05-pytest-sqlite.txt` |
| AI integration gate, 6/6 | `docs/qa/evidence/2026-11-05-ai-integration-gate.txt` |
| Live Milestone 2 outreach/scoring check | `docs/qa/evidence/2026-11-05-milestone2-live-check.json` |
| Outreach and scoring validation notes | [`outreach-scoring-validation.md`](outreach-scoring-validation.md) |
| Docker Compose verification | `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` |
| Browser UI check (earlier UI) | `docs/qa/evidence/2026-10-27-browser-ui-check.txt` |
| Live UAT, 26 October | `docs/qa/evidence/2026-10-26-uat-live-postgres-heuristic.md` |
| Defect log | [`bug-log.md`](bug-log.md) |
| Test plan | [`test-plan.md`](test-plan.md) |
| Test cases | [`test-cases.md`](test-cases.md) |
| Traceability | [`traceability-matrix.md`](traceability-matrix.md) |
| API matrix | [`api-test-matrix.md`](api-test-matrix.md) |
| Database matrix | [`database-test-matrix.md`](database-test-matrix.md) |
| Integration plan | [`integration-test-plan.md`](integration-test-plan.md) |
| AI quality validation | [`ai-quality-validation.md`](ai-quality-validation.md) |
| Regression suite | [`regression-suite.md`](regression-suite.md) |
| UAT plan and results | [`uat-plan.md`](uat-plan.md), [`uat-results.md`](uat-results.md) |

---

## 9. Recommendation

**Recommendation: proceed to the Milestone 2 demonstration for Modules 3 and 4, with the
limitations in section 5 stated openly.**

Conditions:

1. Demonstrate the Outreach Studio from the Compose stack: generate, regenerate, edit,
   copy, save and record-as-sent.
2. Demonstrate scoring and the recommendation panels, and show that
   `conversion_probability` is withheld rather than invented.
3. Do not claim the 85% accuracy target. It requires a labelled dataset and a calibration
   split that do not exist in this build.
4. Do not claim live model calls. Show the labelled mock-provider state instead.
5. Re-run the full suite after any further merge and update this report.

---

## 10. Sign-off

| Role | Name | Status |
|---|---|---|
| QA / Test Engineer | Mohamed Isharak M | Signed - 5 November 2026 |
| Backend owner | M Doran | Pending |
| Database owner | Marri Sai Surekha | Merge verified - owner sign-off pending |
| AI owner | Mahidhar Reddy | Package merged - owner sign-off pending |
| Frontend owner | Maheksaba Akbar Shaikh | UI merged and verified - owner sign-off pending |
