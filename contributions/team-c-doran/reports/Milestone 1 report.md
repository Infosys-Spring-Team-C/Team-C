# Milestone 1 Backend Engineering Completion Report

## SalesGenie AI — Lead Management Foundation

**Author / Role:** M Doran, Backend Developer Lead\
**Execution period in schedule:** October 12–20, 2026 (Days 1–9)
**Milestone:** Milestone 1 — Planning, Design, Lead Management & Evaluation

## 1. Document Header & Executive Summary

Milestone 1 establishes the backend foundation for managing SalesGenie AI leads. The project schedule assigns work across requirements planning, database design, lead CRUD, CSV import with duplicate detection, qualification scoring, frontend integration, testing, and milestone evaluation.

The current repository contains a FastAPI application, SQLAlchemy lead model, Pydantic schemas, lifecycle-aware lead CRUD routes, CSV upload with validation and case-insensitive duplicate checks, and SQLite-backed API tests. This provides a usable lead management and ingestion API foundation.

Repository evidence does not establish that each task was completed on its scheduled day. In particular, no SRS sign-off, API contract document, Docker baseline, Alembic migration scripts, company profile analysis service, Streamlit Leads UI, sample CSV dataset, Infosys demo record, Milestone 1 sign-off, or verified 95%+ management-efficiency metric was found. This report distinguishes available implementation evidence from scheduled targets and items requiring project-team confirmation.

## 2. Milestone 1 Deliverables & Technical Breakdown

| Phase / Date | Core responsibilities & tasks from schedule | Tech stack / modules | Backend deliverables and evidence |
|---|---|---|---|
| Day 1 · Mon, Oct 12 · Planning | Kickoff, requirements, scope finalization, review of six modules, architecture, and database schema | Project planning; architecture and data design | Scheduled deliverable: signed-off SRS. No signed-off SRS or meeting evidence is present in the repository; requires confirmation. |
| Day 2 · Tue, Oct 13 · Planning | Define API contracts, select stack, create Git repo and branching, plan sprint, prepare dev environment and Docker baseline | FastAPI, SQLAlchemy, PostgreSQL-compatible connection configuration, Git | Current API implementation is in `app/api/leads.py`; dependency declarations include FastAPI, SQLAlchemy, and psycopg. A dated API contract, sprint backlog, Docker configuration, and branching policy are not evidenced. Git history exists, but it does not verify the scheduled activities or their dates. |
| Day 3 · Wed, Oct 14 · Design | ER diagram, eight-table PostgreSQL schema, migrations, four Streamlit wireframes, LangGraph agent architecture | SQLAlchemy models; PostgreSQL driver; Streamlit and LangGraph per schedule | Current `database/models.py` contains the `leads` table plus later milestone models. No ER diagram, eight-table Milestone 1 schema, migration scripts, wireframes, or LangGraph architecture artifact is evidenced. |
| Day 4 · Thu, Oct 15 · Development | Implement models and migrations; prospect CRUD with lifecycle stages; company profile analysis service | FastAPI, SQLAlchemy, Pydantic | Lead ORM model and CRUD routes exist. Lifecycle values are validated. Company profile analysis service and migration scripts are not evidenced. |
| Day 5 · Fri, Oct 16 · Development | CSV/manual import and duplicate detection; Leads tab; qualification scoring and Lead Intelligence output | FastAPI, Python CSV module, Pydantic, SQLAlchemy; Streamlit and AI/ML per schedule | Manual lead creation and CSV upload are implemented. CSV input is validated and duplicate matching is case-insensitive on company/contact. Dedicated company qualification or Lead Intelligence service and Streamlit Leads tab are not evidenced. |
| Day 6 · Sat, Oct 17 · Buffer / Review | Unit test CRUD, import, scoring; catch-up; seed sample CSV dataset | pytest, FastAPI TestClient, SQLite test database | Lead API tests cover CRUD, pagination/filtering, CSV duplicate handling, empty files, missing headers, and Windows-1252 encoding. A standalone sample lead dataset and dated seed procedure are not evidenced. |
| Day 7 · Sun, Oct 18 · Buffer / Review | Integrate intelligence into UI; review accuracy; draft test report | Streamlit; AI/ML; QA | No score badge, insights panel, accuracy review, or dated draft Milestone 1 test report is evidenced. Current test suite confirms API behavior, not scoring accuracy. |
| Day 8 · Mon, Oct 19 · Evaluation | Infosys milestone evaluation, demo lead management and intelligence, fix last-minute issues | Full team; FastAPI lead APIs | Lead management API is available in the current source. The scheduled session, demo build, fixes, and evaluation outcome are not evidenced; requires confirmation. |
| Day 9 · Tue, Oct 20 · Evaluation | Submit/review reports; sign-off based on 95%+ manageable records and accurate insights | Project lead, QA, full team | No sign-off artifact, test report submission, dataset-level efficiency measurement, or accuracy result is evidenced. The 95% target cannot be reported as achieved from repository evidence. |

## 3. System Architecture & Core Backend Implementations

### 3.1 Environment Setup & Repository Architecture

The backend application entry point is `main.py`. It creates the FastAPI app, registers API routers, applies CORS configuration for local development, exposes `GET /health`, and handles SQLAlchemy and Pydantic validation errors. `app/database.py` loads environment variables with `python-dotenv`, reads `DATABASE_URL`, creates a SQLAlchemy engine with pre-ping and server-database pool settings, and provides a request-scoped session dependency that closes the session in a `finally` block.

The repository declares FastAPI, SQLAlchemy, PostgreSQL's psycopg driver, Pydantic, and supporting packages in its requirements files. The application can be configured with a PostgreSQL connection URL; the tests use SQLite. The following schedule deliverables are not present in the current repository: Dockerfile or Compose baseline, documented Git branching rules, a standalone endpoint contract document, and a signed-off environment setup record.

### 3.2 Database Design & ORM Models

The `Lead` ORM model in `database/models.py` maps to the `leads` table. It includes an auto-incrementing integer primary key, company and contact attributes, lifecycle status, optional technology/funding/company-size/revenue fields, timestamps, and indexes on company name and status.

Lead lifecycle values exposed through the API schema are `new`, `contacted`, `qualified`, and `closed`. The model is part of SQLAlchemy metadata, but a migration framework and migration scripts were not found. The project schedule calls for an eight-table schema; the current model source defines four tables in total, including models added for later modules. No evidence shows the eight-table Milestone 1 PostgreSQL schema was created or applied to a PostgreSQL instance.

### 3.3 Core API Endpoints — Lead CRUD & Lifecycle Management

| Method | Route | Behavior | Success / relevant error status |
|---|---|---|---|
| `POST` | `/leads/` | Create a lead after Pydantic validation | `201 Created`; invalid request `422` |
| `GET` | `/leads/` | List leads with `skip`, `limit`, and optional status/industry filters | `200 OK` |
| `GET` | `/leads/{lead_id}` | Retrieve a lead by ID | `200 OK`; missing lead `404` |
| `PUT` | `/leads/{lead_id}` | Update supplied fields; lifecycle values are constrained by schema | `200 OK`; missing lead `404`; invalid values `422` |
| `DELETE` | `/leads/{lead_id}` | Permanently delete a lead | `204 No Content`; missing lead `404` |
| `POST` | `/leads/upload-csv` | Validate CSV, skip duplicates, bulk insert valid leads, and summarize errors | `200 OK` with import summary |

The schedule refers to the records as prospects in some tasks; the implementation uses the `Lead` model and `/leads` route prefix. A company profile analysis service is not present in the repository, so no endpoint or service behavior for that item can be confirmed.

### 3.4 Lead Ingestion & Processing Pipeline

The CSV endpoint uses Python's standard `csv` module. It requires `company_name`, `industry`, and `contact_name`; validates each candidate row through `LeadCreate`; accepts UTF-8/UTF-8-with-BOM and falls back to Windows-1252; and reports invalid rows without aborting valid rows. It checks existing records using case-insensitive company/contact pairs and also avoids inserting duplicate pairs repeated within the uploaded file. Valid new records are inserted using SQLAlchemy bulk mapping and committed.

Manual creation is provided by `POST /leads/`. A separate sample CSV dataset, a qualification-score pipeline, and Lead Intelligence output are not evidenced for Milestone 1. Current lead scoring endpoints and models belong to later intelligence functionality and do not by themselves verify that the scheduled Milestone 1 qualification scoring deliverable was completed during Days 4–5.

## 4. Testing, Data Seeding & Milestone Evaluation Readiness

### Test coverage and execution

`tests/test_leads.py` covers lead creation and persistence, missing fields, retrieval, not-found responses, pagination and filters, lifecycle update, deletion, CSV deduplication, empty CSV, missing required headers, and Windows-1252 input. Tests override `get_db` and use an in-memory SQLite engine with SQLAlchemy metadata, isolating the API tests from a production database.

```text
.venv/bin/python -m pytest -q tests/test_intelligence.py tests/test_leads.py
18 passed, 1 warning in 0.53s
```

All 18 tests passed. One Starlette deprecation warning notes that using `httpx` with `starlette.testclient` is deprecated and recommends `httpx2`; it did not fail the suite. The test result verifies the current test cases, not the historical date on which the scheduled Day 6 work was performed.


## 5. Summary of Achievement

### Verified backend outcomes

- FastAPI application and database session infrastructure are present.
- Lead model and typed Pydantic create/update/response schemas are present.
- Lead CRUD routes support pagination, filtering, lifecycle status validation, and not-found handling.
- CSV ingestion supports row validation, duplicate detection, bulk insertion, and Windows-1252 fallback.
- The current project test run passed all 18 tests across the lead and intelligence test files.
