# Milestone 3 Backend Engineering Completion Report

## SalesGenie AI — Module 5: CRM Integration & External Synchronization

**Author / Role:** M. Doran, Backend Developer\
**Execution period in schedule:** October 31–November 10, 2026 (Days 20–30)\
**Target milestone and module:** Milestone 3 — Module 5 (CRM Integration & External Synchronization)\
**Report prepared:** 18 November 2026

---

## 1. Document header and executive summary

The backend scope for Module 5 is the CRM API, provider-neutral field mapping, the
contact/activity/deal-stage sync path with audit logging, and the conversation summarisation
and storage API that the Conversations page reads. The canonical backend in this repository
now implements all of it:

| Signal | Result |
|---|---|
| Module 5 API routes | **12** - CRM providers, field maps, validation, preview, sync, status, logs, retry; conversations summarise, save, list, read |
| CRM API tests | **9 passed** |
| Conversation and interaction tests | **4 passed** |
| Module 5 focused tests | **14 passed**, 45 deselected |
| CRM live-transport tests | **16 passed** (`tests/test_crm_transport.py`, no network) |
| Full suite, SQLite | **191 passed, 7 skipped** |
| Live UAT | **25/25 workflows passed**, including UAT-22 to UAT-25 |
| Live AI gate (Groq) | **6/6 operations**, `used_mock=false`, including `summarize_conversation` |

Two limits are stated openly and are **not** presented as achievements:

1. **The live Salesforce/HubSpot transport is implemented but never exercised against a real
   org.** SRS Decision D-06 still leaves CRM access unconfirmed. The transport
   (`backend/services/crm_transport.py`) performs real HTTP calls when
   `CRM_LIVE_ENABLED=true` and credentials are present, and it is covered by 16 tests with the
   HTTP layer replaced by a fake. Until a sandbox run is captured, `FR-041` and `FR-042` stay
   `PARTIAL`.
2. **The demo and sign-off rows were not completed.** The scheduled evaluation dates passed
   without a recorded session. This report records the implemented and tested backend, not a
   ceremony that did not happen.

The earlier snapshot report under `contributions/team-c-doran/reports/` was written against
the standalone contribution repository and correctly listed missing conversation storage and
UI there. Those gaps do **not** exist in the canonical backend: `sales_interactions`, the
summarise/save/list/read routes and the Conversations page are all present and tested here.

---

## 2. Milestone 3 deliverables and ownership matrix

| Day and date | SDLC phase | Scheduled task | Backend deliverable and evidence |
|---|---|---|---|
| Day 20 · Sat, Oct 31 | Buffer / Review | Close Milestone 2 items; study CRM mapping; prepare transcripts | Field mapping exists in `backend/services/crm.py`; no separate mapping-notes document was produced |
| Day 22 · Mon, Nov 2 | Development | Build the FastAPI CRM endpoints and field mapping | `backend/routers/analytics.py` exposes providers, field maps, validation, preview, sync, status and logs; `backend/schemas.py` validates provider and operation values |
| Day 23 · Tue, Nov 3 | Development | Contact, activity and deal-stage sync with `CRM_Sync_Logs` | `backend/services/crm.py` builds the three record types; `backend/db.py` defines `crm_sync_logs`; every attempt is persisted |
| Day 24 · Wed, Nov 4 | Development | Meeting/call summarisation and `Sales_Interactions` storage | `backend/routers/conversations.py` summarises and persists summary, key points, action items, sentiment and follow-up date |
| Day 26 · Fri, Nov 6 | Testing & QA | Finalise endpoints; exercise the three workflows | 9 CRM tests, 4 conversation tests, UAT-22 to UAT-24; PostgreSQL 16 suite **177 passed** |
| Day 28 · Sun, Nov 8 | Buffer / Review | Prepare demo, fix CRM issues, draft the test report | This report and the Milestone 3 test report were refreshed on 17–18 November |
| Day 29 · Mon, Nov 9 | Milestone Evaluation | Demo CRM integration and call summaries | No demo recording or minutes exist |
| Day 30 · Tue, Nov 10 | Submission / Sign-off | Report submission and sign-off | Still pending |

---

## 3. Technical architecture and core backend implementations

### 3.1 Module 5 API surface

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/v1/crm/providers` | List the supported providers and whether a live transport is configured |
| `GET` | `/api/v1/crm/field-mappings` | Documented Salesforce and HubSpot field maps |
| `POST` | `/api/v1/crm/mappings/validate` | Validate a mapping payload and return per-field errors |
| `POST` | `/api/v1/crm/sync/preview` | Build the provider-neutral payload without writing an audit row |
| `POST` | `/api/v1/crm/sync` | Run a contact, activity or deal-stage sync and write the audit row |
| `GET` | `/api/v1/crm/status` | Report simulated connectivity and the recent failure rate |
| `GET` | `/api/v1/crm/sync-logs` | Return sync history for a lead, newest first |
| `POST` | `/api/v1/crm/sync-logs/{log_id}/retry` | Retry a failed attempt and increment the attempt count |
| `POST` | `/api/v1/conversations/summarize` | Summarise notes or a transcript through the configured engine |
| `POST` | `/api/v1/leads/{lead_id}/conversations` | Persist a summary produced elsewhere |
| `GET` | `/api/v1/leads/{lead_id}/conversations` | List stored interactions for a lead |
| `GET` | `/api/v1/conversations/{interaction_id}` | Read one stored interaction |

Write routes require a valid JWT. The CRM sync, CRM retry and conversation write routes
require the writer role (`admin`, `manager` or `rep`); read routes require any authenticated
user.

### 3.2 Provider-neutral field mapping

`backend/services/crm.py` maps three standardised record types:

| Operation | Record | Mapped fields |
|---|---|---|
| `sync_contact` | `contact` | Company, contact name, lead status |
| `update_stage` | `deal` | Company, contact name, local stage mapped to the provider stage |
| `activity_log` | `activity` | Common lead fields and a SalesGenie sync activity |

The field maps use documented vendor names for both providers (`Account.Name` and
`dealstage` are asserted in the tests). They are documentation-grade: no sandbox org was
available to confirm custom fields.

### 3.3 Sync engine, live transport and audit

`simulate_sync` is deterministic and performs no network I/O. It returns the provider-neutral
record plus `mode: simulated` and an explicit no-external-call note.

`backend/services/crm_transport.py` adds the live path:

| Concern | Implementation |
|---|---|
| Activation | `CRM_LIVE_ENABLED=true` **and** provider credentials; a token alone only changes the reported `configured` state |
| Salesforce | `POST /services/data/v{version}/sobjects/{Lead,Task,Opportunity}/` with a bearer token; payloads omit empty fields and map the lifecycle stage onto documented picklist values |
| HubSpot | `POST /crm/v3/objects/{contacts,tasks,deals}` with `{"properties": {...}}` |
| Retry | `429` and `5xx` retried with exponential backoff, honouring `Retry-After`, up to `CRM_MAX_ATTEMPTS`; `4xx` fails immediately |
| Timeout | `CRM_TIMEOUT_SECONDS` per request |
| Audit | one row per attempt with `mode: live`, HTTP status, attempt count and external record id; the credential is never written |
| Outcome | `200` with per-record status on full or partial success; `502 crm_sync_failed` when every record fails |

The endpoint:

* refuses an unknown provider or operation with `422` and writes no audit row;
* refuses an unconfigured sync with `501 crm_not_configured` rather than pretending to connect;
* persists provider, entity type, operation, status, request/response metadata, error message
  and attempt count for every attempt;
* increments the attempt count on retry and refuses to retry a success;
* leaves the lead and its stored interaction untouched when a sync fails.

`crm_sync_logs.lead_id` uses `ON DELETE SET NULL`, so deleting a lead preserves the audit
history that a sync was attempted.

The live transport has not been pointed at a real org. The 16 tests replace the HTTP layer with
a fake, which proves the mapping, retry and audit behaviour but not vendor acceptance.

### 3.4 Conversation summarisation and storage

`POST /api/v1/conversations/summarize` calls the configured engine and persists a
`sales_interactions` row with the transcript, summary, key discussion points and action
items. `POST /api/v1/leads/{lead_id}/conversations` persists a summary produced elsewhere and
refuses an empty summary. The engine may only extract what the transcript or notes contain; an
invented action item fails the grounding tests. The storage layer does not generate or infer
content, and `sentiment`/`follow_up_date` stay at their defaults because no caller supplies
them yet.

### 3.5 Authentication and error handling

JWT validation uses the configured `JWT_SECRET`, HS256 and the `sub`, `role` and `exp`
claims. Missing or invalid tokens return `401`; insufficient roles return `403`. Domain
errors use a stable `{error, message}` shape and the documented status codes (`404`, `409`,
`422`, `501`, `502`). Provider failures do not leak credentials or stack traces.

---

## 4. Database models

Module 5 writes to two tables, both covered in the DevOps/database report:

* `sales_interactions` - lead foreign key with cascade delete, transcript, summary, JSON key
  points and action items, follow-up date, sentiment, composite `(lead_id,
  interaction_date)` index.
* `crm_sync_logs` - lead foreign key with set-null, provider, entity type, operation,
  external record id, status, JSON request/response metadata, error message, attempt count,
  and indexes on `lead_id`, `status` and `(provider, status)`.

---

## 5. Integration testing, QA and demo readiness

| Check | Result | Evidence |
|---|---|---|
| Module 5 focused suite | **14 passed** | `tests/test_api_ai.py`, `tests/test_frontend_compat.py` |
| CRM API tests | **9 passed** | `tests/test_api_ai.py` |
| Conversation and interaction tests | **4 passed** | `tests/test_api_ai.py` |
| Full suite, SQLite | **191 passed, 7 skipped** | 18 November 2026 run |
| CRM live-transport tests | **16 passed**, no network | `docs/qa/evidence/2026-11-18-pytest-crm-transport.txt` |
| Live UAT | **25/25**, including UAT-22 to UAT-25 | `docs/qa/evidence/2026-11-17-uat-live-milestone3.md` |
| Live AI gate | **6/6**, `used_mock=false` | `docs/qa/evidence/2026-11-17-ai-integration-gate-live-groq.txt` |
| Live CRM transport | **Implemented, not verified against a real org** | `backend/services/crm_transport.py`; D-06 still open |
| Demo and sign-off | **Not completed** | No recording, minutes or sign-off row |

---

## 6. Conclusion and transition to Milestone 4

The backend work is complete in code: all twelve Module 5 routes exist, the three sync
workflows run through either the simulator or the live transport, the conversation summary is
stored and readable, retries and audit rows are implemented, and the suite is green.

What remains is verification against a real CRM, not implementation: a Salesforce developer org
or HubSpot sandbox, confirmation of custom fields, and a captured live run. Until that exists,
`FR-041` and `FR-042` stay `PARTIAL` and no live call is claimed.

---

**Evidence note:** This report describes the canonical backend on 18 November 2026, including
`backend/services/crm_transport.py` and `tests/test_crm_transport.py`. The earlier contribution
snapshot remains in `contributions/team-c-doran/` as an attributable source. The live transport
is unit-tested against a fake HTTP layer only; no live Salesforce or HubSpot call, demo session
or sign-off is claimed.
