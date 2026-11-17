# SalesGenie AI — Backend Service

FastAPI backend for SalesGenie AI, an AI-assisted sales lead management and intelligence platform. The backend provides lead APIs, outreach and scoring services, CRM synchronization endpoints, and analytics APIs for the dashboard.

**Backend owner:** M. Doran

**Stack:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL

**API version:** 1.0.0

## Backend role in the project

The backend owns the API contracts, persistence models, validation, business-service boundaries, access checks, and dashboard data aggregation used by the SalesGenie frontend and AI/ML components.

Current backend capabilities include:

- Lead creation, retrieval, update, deletion, pagination, filtering, and CSV ingestion with duplicate detection.
- Local outreach draft generation and campaign history persistence.
- Lead score calculation and score-card persistence.
- CRM payload mapping, simulated sync, audit logs, and sync status aggregation.
- Analytics for lifecycle counts, conversion rate, estimated pipeline value, and top-scored leads.
- JWT role checks for lead deletion and CRM sync, response compression, and request timing headers.

Some service implementations are local prototypes. Outreach generation and lead scoring use deterministic local logic. CRM synchronization simulates provider results and does not currently make live Salesforce or HubSpot API calls.

## Architecture

```text
main.py                     FastAPI app, middleware, health check, exception handlers
app/
  api/                      Route handlers for leads, outreach, scoring, CRM, analytics
  core/security.py          JWT verification and role authorization dependencies
  schemas/                  Pydantic request and response models
  services/                 Outreach/scoring logic and CRM mapping/simulator
  database.py               Environment loading, SQLAlchemy engine and session dependency
database/models.py           SQLAlchemy models
tests/                      API integration tests using SQLite
reports/                     Milestone work and deliverables reports
```

The application reads `DATABASE_URL` from the environment or `.env`. PostgreSQL is the configured production target. The automated API tests create an isolated SQLite database. SQLAlchemy models are defined in `database/models.py`; this repository does not currently include Alembic migration scripts or an automatic production schema-creation step.

## Local setup

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 2. Configure the environment

Copy `.env.example` to `.env`, then set a valid database URL and a private JWT signing key. Generate a random key with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Example configuration shape:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
JWT_SECRET_KEY=replace-with-the-generated-random-value
```

The application rejects an unset, placeholder, or shorter-than-32-byte JWT secret when a protected endpoint is called. Keep the real `.env` file and signing key out of source control. A trusted authentication issuer must create tokens signed with HS256 and containing `sub`, `role`, and `exp` claims; this backend does not provide a login or token-issuing endpoint.

Before using the API against a new database, provision the tables from the SQLAlchemy models using the project’s database deployment process. No migration command is currently provided.

### 3. Run the API

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

The service listens at `http://127.0.0.1:8000` by default. Interactive API documentation is available at `/docs`; the alternate schema view is at `/redoc`.

## API endpoints

| Area | Method and route | Purpose |
|---|---|---|
| Health | `GET /health` | Liveness response |
| Leads | `POST /leads/` | Create a lead |
| Leads | `GET /leads/?skip=0&limit=20` | List leads; optional `lead_status` and `industry` filters |
| Leads | `POST /leads/upload-csv` | Validate and bulk import CSV leads; skip duplicates |
| Leads | `GET /leads/{lead_id}` | Read one lead |
| Leads | `PUT /leads/{lead_id}` | Update lead fields and lifecycle status |
| Leads | `DELETE /leads/{lead_id}` | Permanently delete a lead; requires `admin` or `manager` JWT role |
| Outreach | `POST /intelligence/outreach` | Generate and persist an outreach draft |
| Outreach | `GET /intelligence/outreach/{lead_id}` | Retrieve campaign history for a lead |
| Scoring | `POST /intelligence/score/{lead_id}` | Calculate or update a lead score card |
| Scoring | `GET /intelligence/score/{lead_id}` | Retrieve the current score card |
| CRM | `POST /crm/sync/{lead_id}` | Map and simulate contact, activity, or deal-stage sync; requires `admin` or `manager` JWT role |
| CRM | `GET /crm/logs/{lead_id}` | Retrieve a lead’s CRM sync history |
| CRM | `GET /crm/status` | Report simulated provider status and recent failure rate |
| Analytics | `GET /analytics/overview` | Lead totals, status breakdown, and conversion rate |
| Analytics | `GET /analytics/pipeline-value` | Estimated open pipeline value grouped by priority |
| Analytics | `GET /analytics/top-leads` | Up to ten leads ordered by score |

### CRM sync example

```http
POST /crm/sync/123
Authorization: Bearer <JWT>
Content-Type: application/json
```

```json
{
  "crm_provider": "salesforce",
  "action": "sync_contact"
}
```

Accepted providers are `salesforce` and `hubspot`. Accepted actions are `sync_contact`, `update_stage`, and `activity_log`. A successful response indicates the local simulator accepted the operation; it does not confirm that an external CRM record was changed.

## Data models

| Table | Purpose |
|---|---|
| `leads` | Lead company/contact profile and lifecycle stage |
| `outreach_campaigns` | Generated outreach drafts and follow-up strategy |
| `lead_scores` | Current score, conversion probability, priority, and scoring factors |
| `crm_sync_logs` | CRM provider/action, mapped payload, status, error, and timestamp |

The database models use foreign keys from outreach campaigns, lead scores, and CRM sync logs to `leads.lead_id`. The score model enforces one current score row per lead.

## Security and performance behavior

- Protected routes accept HS256 bearer JWTs containing `sub`, `role`, and `exp` claims.
- The CRM sync and lead delete operations permit only `admin` and `manager` roles.
- CORS allows the Streamlit dashboard at `http://localhost:8501` and local development origins.
- GZip compression is enabled for responses of at least 500 bytes.
- API responses include `X-Process-Time`; the header is exposed to browser clients through CORS.
- Outreach generation and scoring service calls have a five-second wait deadline. A timeout returns `504 Gateway Timeout`.
- Database errors return a generic `503` response; request validation errors return `422`.

## Testing

Run the full test suite from the project root:

```bash
source .venv/bin/activate
python -m pytest -q
```

Run only a specific API area:

```bash
python -m pytest -q tests/test_leads.py
python -m pytest -q tests/test_intelligence.py
python -m pytest -q tests/test_crm.py
```

The tests use SQLite and FastAPI dependency overrides, so they do not require a running PostgreSQL server or live CRM credentials. CRM tests cover the simulated adapter and do not validate external Salesforce or HubSpot API behavior.

## Project reports

- [Milestone 1 report](reports/Milestone%201%20report.md)
- [Milestone 2 report](reports/Milestone%202%20report.md)
- [Milestone 3 report](reports/Milestone%203%20report.md)

## Known backend follow-up

- Add Alembic migrations and a documented schema upgrade process.
- Implement provider-specific Salesforce and HubSpot adapters, OAuth credential lifecycle, retries, and external sandbox integration tests.
- Define and implement conversation-summary persistence and APIs with the AI/ML and frontend teams.
- Decide whether local deterministic outreach and scoring services will be replaced by production AI/ML providers.
- Add broader authorization policy coverage and operational deployment configuration as the product approaches production.
