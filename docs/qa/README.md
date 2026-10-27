# QA / Test Engineering Pack

**Owner:** Mohamed Isharak M - QA / Test Engineer and Project Lead
**Date:** 26 October 2026
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
| Bug tracking | [`bug-log.md`](bug-log.md) | 16 defects with severity, reproduction, status |
| User acceptance testing | [`uat-plan.md`](uat-plan.md), [`uat-results.md`](uat-results.md) | Personas, workflows, live execution results |
| Milestone reporting | [`milestone-test-report.md`](milestone-test-report.md) | Summary, coverage, limitations, evidence index, sign-off |
| Traceability | [`traceability-matrix.md`](traceability-matrix.md) | Requirement → test case → automated test → status |

---

## 2. Current verified status

| Signal | Value | Source |
|---|---|---|
| Automated tests, SQLite | **150 passed, 6 skipped** | `evidence/2026-10-27-pytest-sqlite-final.txt` |
| Automated tests, PostgreSQL 16 | **156 passed** | `evidence/2026-10-27-pytest-postgres-open-defects.txt` |
| Generated DDL vs Alembic schema | **identical** (110 columns, 6 FKs, 31 indexes) | `evidence/2026-10-26-schema-parity.txt` |
| Live UAT workflows | **20 passed, 1 partial, 0 failed** | `evidence/2026-10-26-uat-live-postmerge.md` |
| Docker Compose stack | **3 services healthy**, API on PostgreSQL 16 | `evidence/2026-10-27-docker-compose-verification.txt` |
| Frontend integration gate | **12/12** with authentication enabled | `evidence/2026-10-27-frontend-integration-gate.txt` |
| Clean install from declared deps | **37 passed** in a fresh virtual environment | `evidence/2026-10-27-clean-install.txt` |
| Defects open | 1 (0 critical, 0 high, 0 medium, 1 low) | [`bug-log.md`](bug-log.md) |
| Requirements fully verified | 35 of 53 FRs | [`traceability-matrix.md`](traceability-matrix.md) |

The 6 skipped tests are the PostgreSQL-only module; they run whenever
`TEST_DATABASE_URL` is set and are the reason the PostgreSQL run collects 156 instead
of 150.

These are the **final milestone** figures. The database contributor's branch
(`origin/team_c_sai`, commit `d4f7fd7`) was merged on 26 October 2026, the canonical
schema was reconciled, and the AI and frontend packages were integrated on 27 October
2026. See [`../database-merge-notes.md`](../database-merge-notes.md) and
[`milestone-test-report.md`](milestone-test-report.md).

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
```

---

## 4. Evidence index

| File | Contents |
|---|---|
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
