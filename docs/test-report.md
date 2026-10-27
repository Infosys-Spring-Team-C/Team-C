# Test Report

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Environment:** Windows, Python 3.10.11, PostgreSQL 16.15 (isolated cluster)
**Repository:** `Team-C`, branch `feature/backend-integration`

Every result below was produced by running the command shown in this environment. Nothing is
inferred or estimated.

> **Post-merge update (26 October 2026).** This report records the run at `711fee3`, before
> the database contributor's branch was merged. The merge and reconciliation were verified
> separately: `116 passed, 6 skipped` on SQLite and `122 passed` on PostgreSQL 16, plus a
> schema-parity check between the generated DDL and the Alembic migration. Current numbers and
> evidence are in [`qa/milestone-test-report.md`](qa/milestone-test-report.md) and
> [`qa/regression-suite.md`](qa/regression-suite.md).

---

## 1. Environment

| Component | Version |
|---|---|
| Python | 3.10.11 |
| FastAPI | 0.162.0 |
| Starlette | 1.7.0 |
| SQLAlchemy | 2.0.55 |
| Alembic | 1.20.1 |
| Pydantic | 2.14.1 |
| psycopg | 3.3.6 |
| PyJWT | 2.15.1 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| PostgreSQL | 16.15 |

Two virtual environments were used:

1. `C:\Users\ishar\AppData\Local\Temp\opencode\audit\Team-C\.venv` - audit environment.
2. `C:\Users\ishar\AppData\Local\Temp\opencode\venv-reqtest` - **clean** environment created only
   from `requirements-dev.txt`, to prove the dependency file is complete.

---

## 2. Baseline - Team-C as committed (`f3724a2`)

```
$ cd C:\Users\ishar\AppData\Local\Temp\opencode\audit\Team-C
$ .\.venv\Scripts\python.exe -m pytest -q
```

Result (actual):

```
==================================== ERRORS ====================================
_________________ ERROR collecting tests/test_backend_api.py __________________
ImportError while importing test module '...\tests\test_backend_api.py'.
...
tests\test_backend_api.py:6: in <module>
    from backend.api import app, get_db
backend\api.py:10: in <module>
    from ai.providers import create_provider
E   ModuleNotFoundError: No module named 'ai'
```

**Conclusion:** the committed application could not be imported. This is the defect the backend
work had to fix first.

---

## 3. Mahidhar's AI package (`dbec717`)

```
$ cd C:\Users\ishar\AppData\Local\Temp\opencode\audit\mahi
$ .\.venv\Scripts\python.exe -m pytest -q
.................                                                        [100%]
17 passed in 1.40s
```

**Conclusion:** his 17 unit tests genuinely pass with the mock provider. No external model was
called.

---

## 4. Sai's repository (`1ff01d9`)

No test directory and no CI workflow exist, so there was nothing to run. The schema was reviewed
statically in [`database-review.md`](database-review.md). No claim of runtime verification is made.

---

## 5. Backend suite - SQLite only

Command:

```powershell
cd C:\projects\infosys\Team-C
$py = "C:\Users\ishar\AppData\Local\Temp\opencode\audit\Team-C\.venv\Scripts\python.exe"
$env:JWT_SECRET = "test-secret-value-0123456789"
& $py -m pytest -q
```

Actual result:

```
111 passed, 6 skipped, 8 warnings in 63.64s
```

The 6 skips are `tests/test_postgres.py`, which skips itself when `TEST_DATABASE_URL` is unset.

Coverage by module (counts from `pytest --collect-only -q`):

| File | Tests | What is verified |
|---|---|---|
| `tests/test_api_leads.py` | 19 | CRUD, validation, lifecycle, aliases, duplicate policy, pagination headers, RBAC, 401/403/404/409/422 |
| `tests/test_api_auth.py` | 10 | PBKDF2 round trip, token issue, expiry, forged signature, inactive user, user administration |
| `tests/test_api_import.py` | 12 | Happy path, aliases, in-file duplicates, DB duplicates, invalid rows, length limits, stage errors, file type, empty file, missing column, non-UTF-8, RBAC |
| `tests/test_api_ai.py` | 29 | Insights persistence, outreach generation/edit/mark-sent, 501 send, scoring honesty, score history, conversation persistence, analytics null KPIs, follow-ups, recommendations, CRM, health, OpenAPI |
| `tests/test_intelligence.py` | 23 | Determinism, bounds, missing-data behaviour, factor weights, no fake probability, outreach channels/tones, conversation honesty, engine selection, external adapter failure |
| `tests/test_external_adapter.py` | 10 | Adapter contract: operation names, outreach key translation, threshold forwarding, error mapping, invalid-output rejection (stub package, not the reviewed code) |
| `tests/test_schema.py` | 8 | Eight models, migration up/down, ORM/migration parity, cascade delete, unique e-mail key, nullable e-mail, JSON round trip |

Warnings (non-failing):

* `StarletteDeprecationWarning` about `httpx` with `TestClient` - a dependency deprecation, not a
  test failure.
* `InsecureKeyLengthWarning` in the forged-token test - the test intentionally uses a short
  attacker secret.
* Alembic `path_separator` deprecation warnings - configuration style, not behaviour.

---

## 6. PostgreSQL integration tests

The system PostgreSQL 16 service on port 5432 requires a password that is not known, and it was
not guessed. An isolated cluster was created instead:

```
initdb -D C:\Users\ishar\AppData\Local\Temp\opencode\pgdata -U postgres --auth=trust --encoding=UTF8 --no-locale
postgres -D ...\pgdata -p 55432 -c listen_addresses=127.0.0.1
CREATE DATABASE salesgenie_test;
```

Verified server:

```
$ psql -w -U postgres -h 127.0.0.1 -p 55432 -c "select version();"
PostgreSQL 16.15 ...
```

Command:

```powershell
cd C:\projects\infosys\Team-C
$py = "C:\Users\ishar\AppData\Local\Temp\opencode\audit\Team-C\.venv\Scripts\python.exe"
$env:JWT_SECRET = "test-secret-value-0123456789"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
& $py -m pytest tests/test_postgres.py -q
```

Actual result:

```
6 passed, 3 warnings in 1.08s
```

What is verified on real PostgreSQL:

1. `alembic upgrade head` creates exactly the eight tables plus `alembic_version`, at revision
   `0001_canonical_schema`.
2. `ON DELETE CASCADE` on `company_insights` and `ON DELETE SET NULL` on `leads.owner_id` and
   `crm_sync_logs.lead_id`.
3. Indexes exist: `ix_leads_email_key`, `ix_leads_stage_created`, `ix_leads_company_contact`,
   `ix_lead_scores_lead_created`, `ix_lead_scores_score_prob`, `ix_outreach_lead_status`,
   `ix_sales_interactions_lead_date`, `ix_crm_sync_provider_status`.
4. ORM round trip and cascade: deleting a lead removes insights, campaigns, scores and
   interactions, and nulls the CRM log.
5. Unique `email_key` raises `IntegrityError`.
6. JSON columns round-trip structured values.

The test module refuses to run against a database whose name does not contain `test`, and it drops
and recreates the `public` schema. It is destructive by design.

---

## 7. Combined suite

```powershell
$env:JWT_SECRET = "test-secret-value-0123456789"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
& $py -m pytest -q
```

Actual result:

```
117 passed, 10 warnings in 69.60s
```

---

## 8. Clean-environment reproducibility

A brand-new virtual environment was created and installed only from the repository:

```powershell
python -m venv C:\Users\ishar\AppData\Local\Temp\opencode\venv-reqtest
& ...\venv-reqtest\Scripts\python.exe -m pip install -r C:\projects\infosys\Team-C\requirements-dev.txt
```

Installed versions matched `requirements-dev.txt` exactly (`fastapi==0.162.0`,
`SQLAlchemy==2.0.55`, `alembic==1.20.1`, `psycopg==3.3.6`, `pydantic==2.14.1`, `PyJWT==2.15.1`,
`pytest==9.1.1`, `httpx==0.28.1`, `uvicorn==0.54.0`, `python-multipart==0.0.32`,
`python-dotenv==1.2.4`).

Full suite in that clean environment:

```
117 passed, 10 warnings in 69.60s
```

**Conclusion:** a clean checkout can be installed and tested from `requirements-dev.txt` alone.

---

## 9. Migration verification

### SQLite

```
$env:DATABASE_URL = "sqlite:///./_mig_test.db"
& $py -m alembic upgrade head
```

Inspected with `sqlite3`:

```
TABLES: ['alembic_version', 'company_insights', 'crm_sync_logs', 'lead_scores', 'leads',
         'outreach_campaigns', 'sales_analytics', 'sales_interactions', 'users']
INDEX_COUNT: 24
```

The automated `test_migration_creates_and_drops_the_schema` also runs `alembic downgrade base` and
asserts the tables are removed.

### PostgreSQL

```
$env:DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
& $py -m alembic upgrade head
```

```
 public | alembic_version    | table | postgres
 public | company_insights   | table | postgres
 public | crm_sync_logs      | table | postgres
 public | lead_scores        | table | postgres
 public | leads              | table | postgres
 public | outreach_campaigns | table | postgres
 public | sales_analytics    | table | postgres
 public | sales_interactions | table | postgres
 public | users              | table | postgres
(9 rows)

indexes: 32
```

---

## 10. Docker

```
$ docker info
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine ...
```

The daemon was not running, so the image was **not built** and `docker compose up` was **not**
executed. Configuration was validated:

```
$ docker compose config --quiet
COMPOSE_CONFIG_EXIT=0
```

**Not verified at the time of this run:** image build, container start, migration inside the
container, health check execution.

**Update, 27 October 2026.** Docker Desktop 29.7.2 became available. `docker compose build`
built both images and `docker compose up -d` started `db`, `api` and `frontend`; all three
reported healthy, the migration ran inside the API container and `/api/v1/health` returned
`status: ok`. See `docs/qa/evidence/2026-10-27-docker-compose-verification.txt` and BUG-012
in `docs/qa/bug-log.md`.

---

## 11. What was not tested

| Item | Reason |
|---|---|
| `SALES_GENIE_AI_BACKEND=external` end to end | `ai/` package is not in Team-C until Mahidhar's PR |
| Real Grok / Gemini / OpenAI calls | No credentials used; no provider was called |
| Email delivery | Not implemented by design (`501`) |
| Live CRM sync | Not implemented by design (`501`) |
| Streamlit frontend | Not delivered |
| Docker image / containers | Daemon unavailable |
| Browser CORS preflight | Not exercised without a browser client |

The external adapter's failure mode **is** tested: constructing it without the package raises
`IntelligenceError` with an actionable message, and `get_engine()` rejects an unknown backend.

---

## 12. Live server smoke test (uvicorn, real HTTP)

The test suite uses `TestClient`, which bypasses a real socket. As an additional check, the app was
started with uvicorn on a throw-away SQLite file and driven with real HTTP requests.

```powershell
$env:DATABASE_URL = "sqlite:///./_smoke.db"
$env:JWT_SECRET = "smoke-test-secret-value-0123456789"
python -m uvicorn main:app --host 127.0.0.1 --port 8123
```

| Step | Result |
|---|---|
| `GET /api/v1/health` | `{"status":"ok","database":"ok","database_dialect":"sqlite","auth_enabled":true,"ai_backend":"heuristic","ai_status":"ok"}` |
| `POST /api/v1/auth/token` | `200`, JWT returned |
| `POST /api/v1/leads` | `201`, `id=1`, `stage=qualified`, `status=Active` |
| `POST /api/v1/leads/1/insights` | `200`, `qualification.category=Qualified`, `engine=heuristic`, 2 supported facts, 3 missing-information items |
| `POST /api/v1/leads/1/scores` | `200`, `56/100`, 4 factors, `conversion_probability=null`, `probability_band=medium` |
| `POST /api/v1/outreach/generate` | `200`, `status=draft`, `channel=Email`, subject generated |
| `GET /api/v1/analytics` | `200`, `total_leads=1`, `conversion_rate=0.0`, `pipeline_value=null` with `pending_definition=true` |
| `POST /api/v1/outreach/send` | `501`, `code=email_transport_not_configured` |
| `GET /api/v1/leads?page=1&page_size=10` | `200` with `x-total-count: 1`, `x-page: 1`, `x-page-size: 10` |
| `GET /api/v1/leads` without a token | `401` |

Uvicorn access log confirmed the same sequence (`201 Created`, `200 OK` x6, `501 Not Implemented`,
`401 Unauthorized`). The server was then stopped and `_smoke.db` deleted; it is git-ignored.

This confirms the application runs as a real server, not only under the test harness. It does not
add coverage of Docker, the external AI engine, e-mail delivery or the frontend.

---

## 13. Reproduce everything

```powershell
cd C:\projects\infosys\Team-C
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

$env:JWT_SECRET = "any-long-random-value"
python -m pytest -q                      # 111 passed, 6 skipped

# optional PostgreSQL
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:PASSWORD@127.0.0.1:5432/salesgenie_test"
python -m pytest -q                      # 117 passed

# live server
python -m alembic upgrade head
python -m backend.cli create-user --email you@example.com --role admin
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
