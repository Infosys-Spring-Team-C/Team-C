# QA / Test Engineering Pack

**Owner:** Mohamed Isharak M - QA / Test Engineer and Project Lead
**Date:** 18 November 2026 (Milestone 3 refresh; CRM live transport and browser walkthrough added)
**Application:** SalesGenie AI (Team C)
**Repository:** `Infosys-Spring-Team-C/Team-C`

This folder holds the test-engineering deliverables for the milestone review. Every
result recorded here was produced by running a command in this repository; nothing is
estimated, inferred or copied from a plan.

---

## 1. Deliverables by responsibility

| QA responsibility | Deliverable | What it contains |
|---|---|---|
| Test planning | [`test-plan.md`](test-plan.md) | Scope, levels, environments, entry/exit criteria, defect workflow, risks |
| Test scenarios and acceptance criteria | [`test-scenarios.md`](test-scenarios.md) | One scenario block per module, each with acceptance criteria |
| Unit testing | [`test-cases.md`](test-cases.md) | `TC-*` cases mapped to the automated test that proves them |
| API testing | [`api-test-matrix.md`](api-test-matrix.md) + [`../postman/`](../../postman) | Endpoint matrix, status codes, negative cases, importable Postman collection |
| Database testing | [`database-test-matrix.md`](database-test-matrix.md) | CRUD, keys, constraints, migrations, generated-DDL parity, integrity on SQLite and PostgreSQL |
| Integration testing | [`integration-test-plan.md`](integration-test-plan.md) | API↔DB, API↔AI, API↔frontend contract, container topology |
| AI quality validation | [`ai-quality-validation.md`](ai-quality-validation.md) | Rubric, determinism, boundary and invalid-output handling |
| Regression testing | [`regression-suite.md`](regression-suite.md) | Exact commands, expected counts, triggers, triage |
| Bug tracking | [`bug-log.md`](bug-log.md) | 20 defects with severity, reproduction, status |
| User acceptance testing | [`uat-plan.md`](uat-plan.md), [`uat-results.md`](uat-results.md) | Personas, workflows, live execution results |
| Milestone reporting | [`milestone-test-report.md`](milestone-test-report.md), [`milestone3-test-report.md`](milestone3-test-report.md) | Summary, coverage, limitations, evidence index, sign-off |
| Traceability | [`traceability-matrix.md`](traceability-matrix.md) | Requirement → test case → automated test → status |

---

## 2. Current verified status

| Signal | Value | Source |
|---|---|---|
| Automated tests, SQLite | **191 passed, 7 skipped** (18 Nov 2026 run) | `evidence/2026-11-17-pytest-sqlite.txt` (175/7 baseline) |
| CRM live-transport tests | **16 passed**, no network | `evidence/2026-11-18-pytest-crm-transport.txt` |
| Automated tests, PostgreSQL 16 | **177 passed** (6 Nov 2026; not re-run on 18 Nov - Docker unavailable) | `evidence/2026-11-06-pytest-postgres.txt` |
| Module 5 focused tests | **14 passed** | `evidence/2026-11-17-pytest-module5-focused.txt` |
| Generated DDL vs Alembic schema | **identical** (110 columns, 6 FKs, 31 indexes) | `evidence/2026-10-26-schema-parity.txt` |
| Live UAT workflows | **25 passed, 0 partial, 0 failed** | `evidence/2026-11-17-uat-live-milestone3.md` |
| Conversations page render (headless) | **PASS** - 7 sections, no exception | `evidence/2026-11-17-conversations-headless-render.txt` |
| Conversations page browser walkthrough | **PASS** - every section rendered, 0 console errors, no horizontal overflow | `evidence/2026-11-18-browser-walkthrough.md` |
| Live AI integration gate (Groq) | **6/6 operations**, `used_mock=false` | `evidence/2026-11-17-ai-integration-gate-live-groq.txt` |
| Docker Compose stack | **3 services healthy**, API on PostgreSQL 16 (27 Oct 2026; not rebuilt 18 Nov) | `evidence/2026-10-27-docker-compose-verification.txt` |
| Frontend integration gate | **12/12** with authentication enabled | `evidence/2026-10-27-frontend-integration-gate.txt` |
| Clean install from declared deps | **37 passed** in a fresh virtual environment | `evidence/2026-10-27-clean-install.txt` |
| Contributor AI suite | **86 passed** from its own folder | `contributions/mahidhar-ai-layer` |
| Contributor backend suite | **24 passed, 1 failed** - BUG-020 (test calls a protected route without a token) | `contributions/team-c-doran` |
| Defects open | 2 (0 critical, 0 high, 0 medium, 2 low) | [`bug-log.md`](bug-log.md) |
| Requirements fully verified | 36 of 53 FRs (7 partial, 9 blocked, 1 not run) | [`traceability-matrix.md`](traceability-matrix.md) |

The 7 skipped tests are 6 PostgreSQL-only tests (they run whenever
`TEST_DATABASE_URL` is set) and 1 opt-in LangGraph memory-checkpointer test whose optional
extra is not installed. The SQLite run therefore passes 191 and skips 7 in the current
198-test suite. Enabling PostgreSQL is expected to give 197 passed and 1 skipped; the last
observed PostgreSQL run, on the older 177-test suite, was 177 passed with no skips.

These are the **current** figures. The Milestone 3 pass re-ran the canonical suite, the
full 25-workflow live UAT and the live AI gate on 17 November 2026, then added 16 CRM
live-transport tests and a Conversations browser walkthrough on 18 November 2026. The
PostgreSQL run and the Compose rebuild could not be repeated because Docker was unavailable. The database
contributor's branch (`origin/team_c_sai`, commit `d4f7fd7`) was merged on 26 October 2026,
and the AI and frontend packages were integrated on 27 October 2026. See
[`../database-merge-notes.md`](../database-merge-notes.md),
[`milestone-test-report.md`](milestone-test-report.md) and
[`milestone3-test-report.md`](milestone3-test-report.md).

---

## 3. How to reproduce

```powershell
# 1. Automated regression suite (SQLite, no server needed)
cd C:\projects\infosys\Team-C
$env:JWT_SECRET = "test-secret-value-0123456789"
python -m pytest -q

# 2. Same suite with the PostgreSQL module enabled
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q

# 3. Live UAT against a running server (see uat-plan.md for setup)
python scripts/qa_uat.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"

# 4. Headless render of the Conversations page against the same server
python scripts/qa_conversations_render.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"

# 5. Live AI gate against Groq (needs the optional openai SDK and a key)
$env:GROQ_API_KEY = "<key from .env>"
$env:SALES_GENIE_LLM_PROVIDER = "groq"
$env:SALES_GENIE_LLM_MODEL = "openai/gpt-oss-120b"
python scripts/check_ai_integration.py
```

---

## 4. Evidence index

| File | Contents |
|---|---|
| `evidence/2026-11-17-environment.txt` | Python, package versions, OS and commit under test |
| `evidence/2026-11-17-pytest-sqlite.txt` | Full pytest output, SQLite, after the Module 5 QA pass |
| `evidence/2026-11-17-pytest-module5-focused.txt` | The 14 Module 5 tests, verbose |
| `evidence/2026-11-17-uat-live-milestone3.md` | Live UAT, 25 workflows, human readable |
| `evidence/2026-11-17-uat-live-milestone3.json` | Same run, machine readable |
| `evidence/2026-11-17-conversations-headless-render.txt` | Headless Streamlit render of the Conversations page, 7 sections |
| `evidence/2026-11-18-browser-walkthrough.md` | Conversations page browser walkthrough: every section rendered with stored data, no console errors, no horizontal overflow |
| `evidence/2026-11-17-browser-walkthrough-attempt.md` | Earlier browser walkthrough attempt, blocked by host memory |
| `evidence/2026-11-17-ai-integration-gate-live-groq.txt` | Live AI gate, 6/6 operations against Groq, `used_mock=false` |
| `evidence/2026-10-26-environment.txt` | Python, package versions, PostgreSQL version, commit under test |
| `evidence/2026-10-26-pytest-sqlite.txt` | Full pytest output, SQLite (pre-merge baseline) |
| `evidence/2026-10-26-pytest-postgres.txt` | Full pytest output, PostgreSQL 16 (pre-merge baseline) |
| `evidence/2026-10-26-pytest-sqlite-postmerge.txt` | Full pytest output, SQLite, after the database merge |
| `evidence/2026-10-26-pytest-postgres-postmerge.txt` | Full pytest output, PostgreSQL 16, after the database merge |
| `evidence/2026-10-26-schema-parity.txt` | Generated `init_schema.sql` vs Alembic, object by object |
| `evidence/2026-10-26-uat-live-postgres-heuristic.md` | Live UAT report, human readable (pre-merge) |
| `evidence/2026-10-26-uat-live-postgres-heuristic.json` | Same run, machine readable |
| `evidence/2026-10-26-uat-live-postmerge.md` | Live UAT report, human readable, after the database merge |
| `evidence/2026-10-26-uat-live-postmerge.json` | Same run, machine readable |

---

## 5. Honesty rules applied to this pack

1. A test is marked `PASS` only if it ran and the output is in `evidence/`.
2. A requirement that is only partly met is marked `PARTIAL` and linked to a defect.
3. Anything that could not run is marked `BLOCKED` or `NOT RUN` with the reason, never
   `PASS`.
4. No accuracy, latency or satisfaction figure is quoted without a defined metric. Where
   the SRS decision is still open (D-10, D-11, D-12, D-13) the report says so.
5. The heuristic engine is never described as a trained or calibrated model.
6. A live model call is only claimed when a gate run recorded `used_mock=false`; a UAT run
   on the heuristic engine is reported as such, not as a model call.
