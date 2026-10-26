# Regression Suite

**Date:** 26 October 2026
**Author:** Mohamed Isharak M

A regression run answers one question: *did this change break something that used to
work?* This document fixes the command, the expected result and the response when the
result differs.

---

## 1. The suite

| Suite | Location | Tests | Time (observed) | Needs a database server |
|---|---|---|---|---|
| Full automated suite | `tests/` | 122 collected (116 on SQLite + 6 PostgreSQL-only) | ~90 s | No (PostgreSQL module skipped) |
| PostgreSQL module | `tests/test_postgres.py` | 6 | included | Yes |
| Database workspace drift | `tests/test_db_workspace.py` | 5 | ~3 s | No |
| Live UAT | `scripts/qa_uat.py` | 21 workflows | ~10 s | Yes, plus a running API |
| External AI gate | `scripts/check_ai_integration.py` | 6 operations | seconds | No, needs the `ai` package or a stub |

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
116 passed, 6 skipped
```

The 6 skips are `tests/test_postgres.py`. They are not failures.

### 2.2 Full regression (PostgreSQL)

```powershell
cd C:\projects\infosys\Team-C
$env:JWT_SECRET = "test-secret-value-0123456789"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q
```

Expected:

```
122 passed
```

If the PostgreSQL port is not listening, the 6 tests error at fixture setup with
`psycopg.errors.ConnectionTimeout`. That is an environment problem, not a code regression;
start the database and re-run before logging a defect.

### 2.3 Live UAT

```powershell
python scripts/qa_uat.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<UAT password>"
```

Expected:

```
20/21 workflows passed, 1 partial
```

The partial is UAT-15, which is **BUG-006**. A run that reports `0 failed` with that one
partial is the current known-good state.

### 2.4 External AI gate

```powershell
python scripts/check_ai_integration.py
```

Expected when the `ai` package is installed: `6/6 operations passed`.
When it is absent the script exits `2` with an actionable SKIP message. That exit code is
the current known state in this repository (**BUG-008**).

---

## 3. Baseline record

| Date | Branch / commit | SQLite | PostgreSQL | UAT | Notes |
|---|---|---|---|---|---|
| 26 Oct 2026 | `feature/backend-integration` @ merge `fbe1fbc` + reconciliation | 116 passed, 6 skipped | 122 passed | 20 passed, 1 partial | **Current known-good baseline** |
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

* **Frontend behaviour.** No UI exists, so UI regressions are invisible.
* **Container startup.** Docker was unavailable, so a Compose regression would not be
  caught.
* **Real AI package behaviour.** The package is absent; only the stub is exercised.
* **Performance regressions.** No benchmark exists, so a slowdown would not fail a test.

These are recorded as limitations in [`milestone-test-report.md`](milestone-test-report.md).
