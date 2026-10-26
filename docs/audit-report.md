# Repository Audit Report

**Project:** SalesGenie AI - AI Sales Assistant & Lead Intelligence Platform
**Organisation:** Infosys-Spring-Team-C
**Audit date:** 26 October 2026
**Auditor:** Mohamed Isharak M (Project Lead / QA)
**Scope:** `Team-C` (canonical), `team_c_sai` (database/DevOps), `team-c-mahi` (AI/ML)

---

## 1. Method and constraints

Each repository was cloned into an isolated workspace outside the project tree:

```
C:\Users\ishar\AppData\Local\Temp\opencode\audit\Team-C
C:\Users\ishar\AppData\Local\Temp\opencode\audit\sai
C:\Users\ishar\AppData\Local\Temp\opencode\audit\mahi
```

Each clone received its own virtual environment. No commit, branch, push, edit or pull request was
made in `team_c_sai` or `team-c-mahi`. The authoritative SRS at `docs/SRS.md` (v1.0, 22 Oct 2026)
was used as the requirements baseline.

The audit distinguishes:

* **Verified** - reproduced by running a command in this environment.
* **Observed** - read directly from the source, not executed.
* **Not verified** - could not be executed (for example, Docker image build with no daemon).

---

## 2. Team-C - baseline state

**Commit:** `f3724a2 chore: retain only files added beyond source ZIP`
**Branches:** `main` only
**Files:** 11 (no `requirements.txt`, no README, no docs)

### 2.1 Baseline test result (verified)

```
$ python -m pytest -q
ImportError while importing test module 'tests/test_backend_api.py'
...
backend\api.py:10: in <module>
    from ai.providers import create_provider
E   ModuleNotFoundError: No module named 'ai'
```

The committed application cannot be imported, let alone started.

### 2.2 Findings

| # | Severity | File | Finding | Evidence |
|---|---|---|---|---|
| C-01 | **Critical** | `backend/api.py` | Imports three modules that do not exist in this repository: `ai.providers`, `ai.graph`, `utils.config`. The app fails at import time. | `api.py:10-12`; pytest traceback above |
| C-02 | **Critical** | repository root | No `requirements.txt`, `pyproject.toml` or lock file. A clean checkout cannot be installed reproducibly. | Directory listing |
| C-03 | **High** | `alembic/versions/0001_core_schema.py` | Migration is a `Base.metadata.create_all()` stub, not a reviewable, versioned DDL migration. It cannot express data migrations, is not dialect-safe, and hides the actual schema from reviewers. | 389-byte file shown below |
| C-04 | **High** | `backend/api.py` | No authentication or authorisation. Every endpoint is public. SRS NFR-005 requires JWT + RBAC. | No security module, no dependency |
| C-05 | **High** | `docker-compose.yml` | Defines a `ui` service that runs `streamlit run app.py`, but `app.py` does not exist in Team-C. `docker compose up` would fail. | compose `ui` service |
| C-06 | **Medium** | `Dockerfile` | No `CMD`, no health check, runs as root, exposes 8501 for a frontend that is not present. | 142-byte file |
| C-07 | **Medium** | `backend/api.py` | CSV import calls `db.rollback()` inside the row loop, discarding earlier successfully imported rows while continuing the loop; the endpoint then raises. Reported counts become unreliable. | `api.py` import block |
| C-08 | **Medium** | `backend/db.py` | Schema omits fields required by Modules 2-4 (website, lifecycle stage, outreach parameters, score factors/explanations, transcript, CRM metadata). | `db.py` models |
| C-09 | **Medium** | `tests/test_backend_api.py` | Single 54-line test module; cannot even be collected. No coverage of auth, import, AI, scoring or analytics. | pytest output |
| C-10 | **Low** | `main.py` | Correct entry point but unusable because of C-01. | - |
| C-11 | **Low** | repository root | No README, `.env.example`, `.gitignore` or contribution guidance. | - |

The stub migration (C-03):

```python
def upgrade():
    Base.metadata.create_all(bind=op.get_bind())
def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
```

### 2.3 Assessment

Team-C as committed is a **non-runnable scaffold**, not an application. Nothing in it could be
demonstrated. The only reusable elements were the intent (FastAPI + SQLAlchemy + Alembic +
PostgreSQL) and the eight-table naming convention, both of which were retained and re-implemented
against the SRS.

---

## 3. Sai Surekha - `team_c_sai`

**Commits:** `1ff01d9 Add files via upload`, `9becb4b Initial commit`
**Structure:** `salesgenie-db-workspace/` with `src/database/models`, `migrations/`,
`init_schema.sql`, `docker-compose.yml`, `er_diagram.html`, `README.md`, `requirements.txt`.

Full file-specific review: [`database-review.md`](database-review.md).

Summary:

| Severity | Finding |
|---|---|
| **High** | Schema cannot support Modules 2-4: `leads` has no website, lifecycle stage, needs, engagement or research fields; `company_insights` stores free text instead of structured intelligence; `lead_scores` has no factor breakdown, priority or model version; `outreach_campaigns` has no tone/length/goal/type/pain-point fields. |
| **High** | Default database password `postgres_password` is committed in `alembic.ini`, `src/database/connection.py` and `docker-compose.yml`. |
| **Medium** | Two competing sources of DDL: `init_schema.sql` and the Alembic migration duplicate the same schema and can drift. |
| **Medium** | `sales_analytics.user_id` is `NOT NULL`, which prevents team-level or global metrics. |
| **Medium** | No tests and no CI workflow; nothing verifies that the migration and ORM models agree. |
| **Low** | `crm_sync_logs.lead_id` is `NOT NULL` with `ON DELETE CASCADE`, so deleting a lead destroys its audit history. |
| **Low** | README instructs other contributors to copy files rather than submit a PR, which breaks attribution. |

**What is reusable:** the eight-table decomposition, index intent, the `ON DELETE CASCADE`
convention for lead-owned records, the PostgreSQL 16 Compose service with a named volume and
`pg_isready` health check, and the Alembic tooling layout. These are reflected in the canonical
implementation, but the schema itself was redesigned from the SRS rather than copied.

---

## 4. Mahidhar Reddy - `team-c-mahi`

**Commit:** `dbec717 Delete .venv directory`
**Structure:** `ai/` (graph, providers, schemas, agents, prompts, scoring), `utils/`,
Streamlit `app.py` + `pages/` + `components/`, `services/api_client.py`,
`integrations/backend_adapter.py`, `tests/`.

Full file-specific review: [`ai-review.md`](ai-review.md).

### 4.1 Verified test result

```
$ python -m pytest -q
.................                                                        [100%]
17 passed in 1.40s
```

The suite genuinely passes in an isolated environment with `pydantic`, `pytest`, `httpx`,
`python-dotenv`, `numpy`, `langgraph` and `openai` installed.

### 4.2 Summary

| Severity | Finding |
|---|---|
| **High** | The AI package is not present in Team-C, so the backend cannot import it (C-01). It must arrive through Mahidhar's PR. |
| **High** | No backend, database or persistence. The package is a library plus a Streamlit demo. |
| **Medium** | `ai/scoring/rule_based.py` implements **eight** factors (`company_fit`, `industry_relevance`, `company_size`, `contact_role`, `engagement_history`, `explicit_needs`, `sales_stage`, `response_behavior`), while SRS FR-030 requires four scoring dimensions (engagement, fit, intent, decision readiness). The eight factors are defensible but need mapping or an SRS decision. |
| **Medium** | No conversion-probability output at all; the score model correctly states it is not a probability, which matches the honesty requirement. |
| **Medium** | `utils/config.py` reads `st.secrets` and `st.session_state`, coupling the AI layer to Streamlit. A backend cannot use it unchanged. |
| **Medium** | Provider retries exist for transient failures (`request_retries`, exponential backoff) but the HTTP clients have no explicit per-request timeout for Gemini (`genai.Client` created without one) and no handling for rate-limit headers. |
| **Low** | `ai/graph.py` gracefully falls back to a non-LangGraph executor when LangGraph is absent. Good for robustness, but it means the graph is not always exercised. |
| **Low** | Prompts live in `ai/prompts/templates.py` and are maintainable; no secrets are embedded. |

**What is reusable:** the agent boundaries, the structured Pydantic schemas, the
research/qualification/outreach/conversation/follow-up/sales-insight operation routing, the
provider abstraction with a deterministic mock, the prompt templates, the scoring heuristics, and
the 17 tests. The backend integration uses these through an adapter rather than copying them.

---

## 5. Cross-repository conflicts

| Area | Team-C (baseline) | Sai | Mahidhar | Resolution |
|---|---|---|---|---|
| Table names | 8 tables | 8 tables (different columns, `*_id` names) | none | Canonical 8 tables in Team-C, with `id` primary keys and explicit FKs |
| Lead lifecycle | `status` string | `lead_status` string | `stage` string | Single canonical `lifecycle_stage`; `stage` exposed in API; `status` derived |
| AI import | `from ai.*` at module import | none | `ai.*` package exists | Adapter with lazy import; default offline engine |
| Config | `utils.config` | `os.getenv` | Streamlit-aware `utils.config` | `backend.config` owns backend settings |
| Migration | `create_all()` stub | SQL + Alembic duplication | none | Single explicit Alembic revision |
| Auth | none | `users` table without password | token passthrough only | JWT + PBKDF2 + RBAC in backend |
| Frontend | compose `ui` service | none | Streamlit demo | No UI in this repository; frontend PR pending |

---

## 6. Integration order adopted

1. Establish the canonical schema and migration from the SRS (done).
2. Implement the backend, auth, services and tests (done).
3. Define the intelligence contract and ship a deterministic engine (done).
4. Accept Mahidhar's `ai/` package through his PR, then enable
   `SALES_GENIE_AI_BACKEND=external` and run the adapter tests (pending).
5. Accept Sai's migration/index/CI improvements through her PR, rebased onto the canonical
   schema (pending).
6. Accept Maheksaba's Streamlit frontend and wire it to `/api/v1` (pending).

---

## 7. What the audit changed in Team-C

* Replaced the non-importable `backend/api.py` with an application factory and seven routers.
* Added `backend/config.py`, `security.py`, `deps.py`, `errors.py`, `schemas.py`, `cli.py`.
* Rebuilt `backend/db.py` as the canonical eight-table model with indexes and cascade rules.
* Replaced the `create_all()` migration with explicit DDL.
* Added the intelligence boundary (`contract.py`, `heuristic.py`, `external.py`).
* Added transactional CSV import, duplicate policy and analytics services.
* Added 117 tests and verified them on SQLite and PostgreSQL 16.
* Added `requirements*.txt`, `.env.example`, `.gitignore`, a non-root `Dockerfile` and a
  corrected two-service `docker-compose.yml`.
* Removed the nonexistent `ui` service and the failing legacy test module.

---

## 8. Items that could not be verified

| Item | Reason | Impact | Smallest next step |
|---|---|---|---|
| Docker image build / `docker compose up` | Docker daemon not running (`npipe:////./pipe/dockerDesktopLinuxEngine` unavailable) | Packaging is configuration-validated but not runtime-verified | Start Docker Desktop, then `docker compose up --build` |
| `SALES_GENIE_AI_BACKEND=external` | `ai/` package not in Team-C | Adapter compiles and fails loudly, but no end-to-end run | Merge Mahidhar's PR, set the flag, run the adapter tests |
| GitHub push / PR | `gh auth status` reports no logged-in host | Work is committed locally only | Authenticate `gh`, push the feature branch |
| Streamlit frontend | Not delivered | Backend is standalone and documented for integration | Maheksaba's PR |

Exact commands and outputs: [`test-report.md`](test-report.md). Git state:
[`git-report.md`](git-report.md).
