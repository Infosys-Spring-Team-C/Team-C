# Regression Suite

**Date:** 17 November 2026
**Author:** Mohamed Isharak M

A regression run answers one question: *did this change break something that used to
work?* This document fixes the command, the expected result and the response when the
result differs.

---

## 1. The suite

| Suite | Location | Tests | Time (observed) | Needs a database server |
|---|---|---|---|---|
| Full automated suite | `tests/` | 198 collected (191 passed + 7 skipped on SQLite) | ~8 min | No (PostgreSQL module skipped) |
| PostgreSQL module | `tests/test_postgres.py` | 6 | included | Yes |
| Database workspace drift | `tests/test_db_workspace.py` | 5 | ~3 s | No |
| Live UAT | `scripts/qa_uat.py` | 25 workflows | ~15 s | Yes, plus a running API |
| Conversations page render | `scripts/qa_conversations_render.py` | 7 sections | ~10 s | Yes, plus a running API |
| External AI gate | `scripts/check_ai_integration.py` | 6 operations | seconds | No, needs the `ai` package or a stub |
| Contributor AI suite | `contributions/mahidhar-ai-layer/` | 86 | ~90 s | No |
| Contributor backend suite | `contributions/team-c-doran/` | 25 | ~4 s | No (24 passed, 1 failed - BUG-020) |

`pytest.ini` at the repository root excludes `contributions/` from root collection
(BUG-019): the contributor archives have their own import roots and reuse module names.
Run them from inside their own folders.

---

## 2. Commands

### 2.1 Standard regression (SQLite)

```powershell
cd C:\projects\infosys\Team-C
$env:JWT_SECRET = "test-secret-value-0123456789"
python -m pytest -q
```

Expected:

```
191 passed, 7 skipped
```

Of the 7 skips, 6 are `tests/test_postgres.py` and 1 is the opt-in LangGraph
memory-checkpointer test. They are not failures.

### 2.2 Full regression (PostgreSQL)

```powershell
cd C:\projects\infosys\Team-C
$env:JWT_SECRET = "test-secret-value-0123456789"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q
```

Expected:

```
177 passed, 0 skipped   # last observed, 6 November 2026
197 passed, 1 skipped   # expected with the current 198-test suite; not yet observed
```

The 197/1 line is arithmetic, not an observed run: 191 SQLite passes plus the 6 PostgreSQL
tests, with the opt-in LangGraph test still skipping. Re-run on a host with PostgreSQL before
quoting it as a result.

If the PostgreSQL port is not listening, the 6 PostgreSQL tests error at fixture setup with
`psycopg.errors.ConnectionTimeout`. That is an environment problem, not a code regression;
start the database and re-run before logging a defect.

### 2.3 Live UAT

```powershell
python scripts/qa_uat.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"
```

Expected:

```
25/25 workflows passed
```

UAT-22 to UAT-25 cover the Module 5 CRM surface: field mappings for both providers, the
three simulated sync workflows, the rejected-operation path and the Conversations page
contract. A run that reports `0 failed` is the current known-good state: **177 passed** on
PostgreSQL (6 November 2026, before the current 198-test suite) and **191 passed, 7 skipped**
on SQLite (18 November 2026).

### 2.4 Conversations page render (headless)

```powershell
python scripts/qa_conversations_render.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"
```

Expected:

```
PASS - 7 sections rendered with live data, no exception, simulated-transport disclaimer present.
```

The script creates a probe prospect with one stored summary and three simulated syncs,
runs `frontend/app.py` through Streamlit's `AppTest` harness, asserts that the seven
Conversations sections reach the rendered element tree, then deletes the probe. It is a
render check, not a browser walkthrough: it does not judge layout or styling. A
`missing ScriptRunContext` warning is expected in bare mode.

### 2.5 External AI gate

```powershell
# Live Groq (needs the optional openai SDK and a key in .env)
$env:GROQ_API_KEY = "<key from .env>"
$env:SALES_GENIE_LLM_PROVIDER = "groq"
$env:SALES_GENIE_LLM_MODEL = "openai/gpt-oss-120b"
python scripts/check_ai_integration.py
```

Expected when the `ai` package and the `openai` SDK are installed with a live key:
`6/6 operations passed`, every line reporting `engine=external` and `used_mock=False`.
Verified on 17 November 2026 - see `evidence/2026-11-17-ai-integration-gate-live-groq.txt`.
With no key the provider falls back to the deterministic mock and the script says so.
When the `ai` package itself is absent the script exits `2` with an actionable SKIP message
(**BUG-008**, closed: the package is installed and the gate now runs).

---

## 3. Baseline record

| Date | Branch / commit | SQLite | PostgreSQL | UAT | Notes |
|---|---|---|---|---|---|
| 18 Nov 2026 | `main` + CRM live transport | 191 passed, 7 skipped | not run (Docker down) | not re-run | **Current known-good baseline**; 16 new transport tests, CI workflow added |
| 17 Nov 2026 | `main` @ `4509814` + live gate | 175 passed, 7 skipped | not run (Docker down) | 25/25 passed | BUG-019 fixed, BUG-020 logged; live AI gate 6/6 (`used_mock=false`) |
| 6 Nov 2026 | `main` @ `cf56b9f` + Groq provider | 171 passed, 6 skipped | 177 passed | 20 passed, 1 partial | Milestone 2 baseline |
| 26 Oct 2026 | `feature/backend-integration` @ merge `fbe1fbc` + reconciliation | 116 passed, 6 skipped | 122 passed | 20 passed, 1 partial | Pre-Milestone 2 baseline |
| 26 Oct 2026 | `feature/backend-integration` @ `711fee3` | 111 passed, 6 skipped | 117 passed | 20 passed, 1 partial | Pre-merge baseline |
| 26 Oct 2026 | `f3724a2` (baseline as committed) | collection error | not run | not run | `ModuleNotFoundError: No module named 'ai'` - BUG-001 |

A regression run is compared against the most recent row. Any drop in the pass count is a
regression until proven otherwise.

---

## 4. When to run

| Trigger | Suite |
|---|---|
| Any change to `backend/` | 2.1 and 2.2 |
| Any change to `alembic/` or `backend/db.py` | 2.1, 2.2, plus `alembic upgrade head` and `alembic downgrade base` |
| Any change to a database model | 2.1, 2.2, and `python scripts/render_db_workspace.py --check` |
| Any change to `backend/intelligence/` | 2.1, 2.2, and 2.4 |
| Any change to an API response shape | 2.1, 2.2, 2.3, and update `docs/api-contract.md` |
| Before opening a pull request | 2.1 and 2.2 |
| Before merging any contributor's pull request | 2.1, 2.2, 2.3, 2.4 |
| Before a milestone demonstration | All four |

---

## 5. Triage procedure

When the result differs from the baseline:

1. **Read the failure, do not guess.** Open the full output, not only the summary line.
2. **Classify** with the table below.
3. **Do not weaken the test to make it pass.** A test that asserted correct behaviour and
   now fails is reporting a real change in behaviour.
4. **Log it.** If it is a defect, add a row to [`bug-log.md`](bug-log.md) with a
   reproduction and a commit reference.
5. **Re-run after the fix**, and record the new result in the baseline table.

| Symptom | Most likely cause | Action |
|---|---|---|
| `ConnectionTimeout` on `test_postgres.py` | Database not running | Start the database, re-run |
| `ModuleNotFoundError: No module named 'ai'` | External engine selected but package absent | Unset `SALES_GENIE_AI_BACKEND` or install the package |
| `KeyError: 'JWT_SECRET'` at import | Secret not set | Set `JWT_SECRET` (the test suite sets it itself; this only happens outside pytest) |
| One assertion fails after a merge | Real behaviour change | Investigate the diff; do not relax the assertion |
| All tests error at import | Broken import in `backend/` | Run `python -c "import main"` first |
| `alembic` reports multiple heads | Two migrations branched | Merge the heads, do not delete a migration |

---

## 6. Flakiness policy

The suite has no known flaky tests. If a test fails intermittently:

1. Run it three times in isolation.
2. If it passes, the test depends on ordering, time or a shared fixture - fix the test.
3. Never mark a flaky test as `skip` without a linked defect.

The live UAT runner generates unique e-mail addresses and unique company names per run, so
re-running it against the same database does not produce false duplicate failures.

---

## 7. What regression testing cannot cover

* **Rendered UI behaviour.** The adapter and page contract are tested, and Streamlit
  `AppTest` runs headless, but no test asserts that a pixel looks right. The new
  Conversations sections have not been walked through in a browser (Docker was unavailable
  on 17 November 2026).
* **Container startup.** The Compose stack was verified on 27 October 2026 and again for
  Milestone 2, but it was not rebuilt in this pass.
* **Real AI provider behaviour.** The suite runs the deterministic engine. The live Groq
  path is exercised by `scripts/check_ai_integration.py`, not by pytest.
* **Performance regressions.** No benchmark exists, so a slowdown would not fail a test.
* **Live CRM transport.** It does not exist (SRS D-06), so no regression can be caught
  there. The simulator and its audit rows are covered.

These are recorded as limitations in [`milestone3-test-report.md`](milestone3-test-report.md).
