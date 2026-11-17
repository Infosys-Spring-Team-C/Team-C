# Milestone 3 Backend Engineering Completion Report

## SalesGenie AI — Module 5: CRM Integration & External Synchronization

**Author / Role:** M. Doran, Backend Developer\
**Execution period in schedule:** October 31–November 10, 2026 (Days 20–30)\
**Target milestone and module:** Milestone 3 — Module 5 (CRM Integration & External Synchronization)

## 1. Document Header & Executive Summary

The schedule assigns backend work for clearing open Milestone 2 items, defining Salesforce/HubSpot field mapping, building CRM API endpoints, implementing synchronization and audit logging, testing workflows, and supporting the Milestone 3 demo.

The repository contains a FastAPI CRM router, Pydantic request and response schemas, a provider-neutral field mapper, a simulated synchronization service, and a SQLAlchemy `crm_sync_logs` model. The sync endpoint supports three actions—contact synchronization, activity logging, and deal-stage updates—and records the attempted payload, result, error message, and timestamp. CRM synchronization requires a valid JWT with an `admin` or `manager` role. The CRM test suite passed all seven tests in the run recorded below.

The current architecture is a request-driven prototype. The CRM service simulates provider responses. The repository also lacks the scheduled `Sales_Interactions` persistence model, call-summary service, Streamlit Conversations UI, demo artifacts, and evaluation/sign-off records. The open Milestone 2 backlog closure and CRM mapping notes are not independently evidenced. Accordingly, this report records verified implementation and test results without treating scheduled work as proof of completion.

## 2. Milestone 3 Deliverables & Ownership Matrix

| Day & date | SDLC phase | Key scheduled tasks | Collaborating roles | Technical deliverables produced / evidence |
|---|---|---|---|---|
| Day 20 · Sat, Oct 31 | Buffer / Review | Close open Milestone 2 items; study Salesforce/HubSpot mapping; prepare sample call transcripts | Backend Developer + AI/ML Engineer | Provider-neutral field mapping exists in `app/services/crm_service.py`. No mapping-notes document, sample transcripts, or record of Milestone 2 issue closure was found. |
| Day 22 · Mon, Nov 2 | Development | Build FastAPI CRM endpoints and Salesforce/HubSpot field mapping | Backend Developer | `app/api/crm.py` exposes sync, history, and status routes; `app/schemas/crm.py` validates provider and action values. Sync is simulated. |
| Day 23 · Tue, Nov 3 | Development | Implement contact, activity, and deal-stage sync logic with `CRM_Sync_Logs` | Backend Developer + Database/DevOps Engineer | Three action mappings and CRM audit persistence are implemented in `app/services/crm_service.py`, `database/models.py`, and `app/api/crm.py`. There are no live provider requests. |
| Day 26 · Fri, Nov 6 | Testing & QA | Finalize external endpoints; exercise contact, activity, and stage workflows; prepare CRM sync test notes | Backend Developer + QA Engineer | `tests/test_crm.py` tests the three action types through the local simulator, including persistence and failure cases. The test run recorded in this report occurred Nov 16; external-provider workflow tests and separate sync notes are not present. |
| Day 28 · Sun, Nov 8 | Buffer / Review | Prepare demo, fix CRM issues, draft Milestone 3 test report | QA Engineer + Backend Developer | This report was prepared Nov 16 and records the current test run. No separate demo build or evidence of a Nov 8 report/demonstration was found. |
| Day 29 · Mon, Nov 9 | Milestone Evaluation (Infosys) | Demo CRM integration and call summaries | Full Team | No demo build, recording, minutes, or evaluation result was found in the repository. |

The schedule also includes Day 21 sprint planning and summarization prompt design (Project Lead + AI/ML Engineer), Day 24 meeting/call summarization and `Sales_Interactions` storage (AI/ML Engineer), Day 25 Streamlit Conversations UI (Frontend Developer), Day 27 summary quality review (AI/ML Engineer + QA Engineer), and Day 30 report submission/sign-off (Project Lead + QA Engineer). These items are included in the scope discussion below where they affect backend integration, but they are not backend-owned schedule rows in the supplied responsibilities.

## 3. Technical Architecture & Core Backend Implementations

### 3.1 Milestone 2 Stabilization & CRM Schema Mapping

The schedule calls for clearing open Milestone 2 items and documenting Salesforce/HubSpot field mappings. The repository includes a provider-neutral mapper for three CRM object types:

| Action | Standardized record | Fields mapped |
|---|---|---|
| `sync_contact` | `contact` | `company_name`, `contact_name`, `lead_status` |
| `update_stage` | `deal` | `company_name`, `contact_name`, local `lead_status` mapped to `stage` |
| `activity_log` | `activity` | Common lead fields and a static SalesGenie synchronization activity description |

These are shared internal payload shapes. There are Salesforce and HubSpot field/property maps, external record IDs, mapping notes, or credentials in the repository. The code therefore demonstrates the mapping boundary, but it does not demonstrate provider-specific field mapping or completed Milestone 2 backlog closure.

### 3.2 CRM Integration FastAPI Endpoints

| Method | Route | Function | Access / response behavior |
|---|---|---|---|
| `POST` | `/crm/sync/{lead_id}` | Map a selected action, invoke the sync adapter, and save an audit entry | Requires JWT role `admin` or `manager`; `201 Created`; missing lead `404`; invalid request `422` |
| `GET` | `/crm/logs/{lead_id}` | Return the selected lead's sync history, newest first | `200 OK`; missing lead `404` |
| `GET` | `/crm/status` | Report simulated provider connectivity and recent failure rate | `200 OK`; aggregates the previous 24 hours |

`CRMSyncRequest` constrains providers to `salesforce` and `hubspot`, and actions to `sync_contact`, `update_stage`, and `activity_log`. Response schemas validate sync status and expose the persisted payload and error details. The paths are not version-prefixed (for example, there is no `/v1` prefix).

JWT validation uses the configured `JWT_SECRET_KEY`, HS256, and required `sub`, `role`, and `exp` claims. The CRM endpoint accepts an application token; Salesforce and HubSpot OAuth credentials and token refresh are not implemented. No provider credentials are stored in the repository.

### 3.3 CRM Synchronization Engine

The endpoint performs synchronization inline in the request path. It loads the lead, builds the standardized payload, and calls `crm_service.simulate_crm_sync`. Successful and failed attempts are written to `crm_sync_logs`. Adapter exceptions are caught and stored as failed attempts with an error message.

There are no background workers, queue, event subscription/webhook receiver, retry scheduler, idempotency key, or outbound HTTP client for Salesforce or HubSpot. The implementation exercises the service boundary and audit lifecycle locally; it does not establish external or bidirectional synchronization.

### 3.4 Cross-Module Data Persistence and Streamlit Support

The CRM status route can provide simulated connectivity and recent local sync statistics for a dashboard consumer. The backend repository does not contain a meeting-summary endpoint, transcript-processing service, `Sales_Interactions` model/table, or conversation history API for a Streamlit Conversations tab. These are scheduled under AI/ML and Frontend roles, with shared data persistence requiring a separate backend contract and implementation.

## 4. Database Schema & Logging Models

### `crm_sync_logs` — implemented ORM model

| Column | SQLAlchemy type | Constraint / purpose |
|---|---|---|
| `log_id` | Integer | Primary key; auto-increment |
| `lead_id` | Integer | Required foreign key to `leads.lead_id`; indexed; cascade delete |
| `crm_provider` | String | Required and indexed; request schema allows Salesforce or HubSpot |
| `sync_type` | String | Required; stores contact push, deal update, or activity log category |
| `status` | String | Required and indexed; response schema restricts values to `success` or `failed` |
| `payload` | JSON | Required; stores the provider-neutral mapped request payload |
| `error_message` | Text | Optional; records adapter failure details |
| `synced_at` | DateTime with timezone | Required, indexed; defaults to current time |


## 5. Integration Testing, QA & Demo Readiness

### CRM test execution

The CRM integration suite was run in the project virtual environment:

```text
.venv/bin/python -m pytest -q tests/test_crm.py
.......                                                                  [100%]
7 passed, 1 warning in 0.46s
```

All seven tests passed. Coverage includes:

- Missing bearer token returns `401`; a user with a non-permitted role receives `403`.
- A manager can run a deal-stage sync; the standardized payload and audit record are checked.
- An admin sync failure is stored and included in the recent failure-rate calculation.
- Contact and activity sync attempts are persisted and returned in per-lead history.
- A missing lead returns `404`; an unsupported provider returns `422`.

Tests use an in-memory SQLite database and the local simulated adapter. They do not test Salesforce/HubSpot credentials, network calls, external-side effects, retries, or production PostgreSQL behavior. One Starlette deprecation warning notes that using `httpx` with `starlette.testclient` is deprecated and recommends `httpx2`; it did not affect the result.

The test run verifies the current CRM API prototype. It does not verify that the Nov 6 test execution, Nov 8 demo preparation, or Nov 9 Infosys evaluation occurred on the scheduled dates. No demo build, demo session evidence, separate QA test notes, or milestone sign-off artifact was found.

## 6. Conclusion & Transition to Milestone 4 / Final Phase

The backend provides a tested CRM synchronization prototype with role-restricted sync requests, provider-neutral contact/activity/deal mapping, and persisted audit logs. The seven CRM tests passed in the recorded run.

Before treating external CRM integration as complete, implement provider-specific Salesforce and HubSpot adapters, credential handling, external sandbox workflows, and operational retry/error controls. Coordinate a `Sales_Interactions` schema and API with the AI/ML summarization component and Streamlit Conversations screen. Record the demo, test notes, and formal sign-off as project artifacts. These items form the backend handoff and hardening work for the next milestone and final integration phase.

---

**Evidence note:** This report is based on the supplied Milestone 3 schedule and backend repository artifacts reviewed November 16, 2026. Scheduled tasks are not treated as evidence of completion. Test results apply to the local simulated CRM adapter and the SQLite test database.
