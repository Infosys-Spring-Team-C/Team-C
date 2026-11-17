# Backend Engineering Work & Deliverables Report

## SalesGenie AI — Milestone 2

**Author:** M Doran, Backend Developer\
**Reporting period:** October 21–29, 2026

**Target milestone:** Milestone 2 — AI Outreach & Lead Intelligence

## 1. Executive Summary

The project schedule assigns backend work for AI outreach generation, outreach endpoints, lead scoring, and Milestone 2 demo support. The repository contains FastAPI routes and SQLAlchemy models for outreach generation and lead scoring, along with deterministic local service implementations.

The backend supports generating and storing an outreach draft, retrieving a lead’s outreach history, calculating and persisting a score card, and retrieving the current score card. These APIs provide a foundation for frontend integration. The repository does not evidence a Streamlit outreach screen or separate edit, copy, refresh, and send workflows. It also does not establish that every scheduled task was completed on its assigned date or that the Milestone 2 demo was conducted.

## 2. Scope & Backend Ownership Breakdown

| Task ID / Date | Module | Scheduled task | Backend responsibilities | Deliverables and evidence |
|---|---|---|---|---|
| M2-01 · Wed, Oct 21 | AI Outreach | Build email generation service and campaign storage | Define request/response contracts, invoke generation service, persist generated drafts | `POST /intelligence/outreach`; `outreach_campaigns` model; deterministic local generator |
| M2-02 · Thu, Oct 22 | Outreach integration | Build outreach endpoints and integrate with Streamlit UI | Provide endpoints for draft generation and campaign history; coordinate API contract with frontend | Generation and history routes exist. Streamlit UI and edit/copy/send routes are not evidenced in the repository |
| M2-03 · Fri, Oct 23 | Lead scoring | Implement score and conversion probability persistence | Pass lead attributes to scoring service, validate results, insert or update score card | `POST /intelligence/score/{lead_id}` and `GET /intelligence/score/{lead_id}`; `lead_scores` model |
| M2-04 · Thu, Oct 29 | Milestone 2 | Demo preparation and integration support | Support integration, review API behavior, resolve defects for demo | Schedule identifies the demo deliverable. Repository evidence does not confirm the demo or its completion |

## 3. Detailed Technical Architecture & API Specifications

### Architecture Overview

The backend uses FastAPI routers, Pydantic request and response schemas, SQLAlchemy ORM models, and a database session dependency. Outreach and scoring logic are called through `app.services.ai_service`, keeping service behavior separate from route handling.

The current service functions provide deterministic local behavior. They establish API contracts that could be connected to an external AI or machine-learning model while preserving the route shape, provided the service input and output contracts remain compatible.

### 3.1 Outreach Generation API Service

**Route:** `POST /intelligence/outreach`\
**Success status:** `201 Created`

**Request example:**

```json
{
  "lead_id": 123,
  "tone": "professional",
  "focus_points": "improving sales team productivity"
}
```

- `lead_id` is required and must be positive.
- `tone` defaults to `professional`.
- `focus_points` is optional.
- A nonexistent lead returns `404 Not Found`.

The route loads the lead, assembles available lead attributes and supplied focus points, then calls `ai_service.generate_outreach_email(lead_data, tone)`. The returned subject, email body, follow-up strategy, tone, and lead ID are saved as an `OutreachCampaign` record and returned in the response.

The current generator uses contact name, company name, industry, focus points, and tone. It produces a deterministic draft and follow-up suggestion. Schedule-requested prompt controls for length, type, goal, pain points, and industry-specific templates are not all represented as explicit request fields or prompt-template options in the current implementation.

### 3.2 Outreach Endpoints & Frontend Integration

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/intelligence/outreach` | Generate and save a draft for a lead |
| `GET` | `/intelligence/outreach/{lead_id}` | Return a lead’s saved campaign history, newest first |

These routes support draft generation and history retrieval. The schedule also calls for Streamlit UI actions to refresh, edit, copy, and send an email. The repository does not evidence a Streamlit screen or distinct backend operations for editing a saved campaign, copying content, refreshing a draft, or sending an email.

### 3.3 Lead Scoring Engine Integration

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/intelligence/score/{lead_id}` | Calculate and persist a score card; update the existing card for that lead |
| `GET` | `/intelligence/score/{lead_id}` | Return the lead’s current score card |

The scoring route loads the lead profile and passes available attributes—including funding stage, company size, technology stack, revenue, and lead status—to `ai_service.score_lead(lead_dict)`. The response is validated with a Pydantic schema before persistence. Invalid service output returns `502 Bad Gateway`; a missing lead returns `404 Not Found`.

The service currently calculates a transparent baseline score from profile completeness and lead status. It derives a conversion probability from the score and assigns a high, medium, or low priority. The implementation is a baseline heuristic; repository evidence does not demonstrate a trained model or separately measured engagement, intent, and decision-readiness features.

## 4. Database Schema & Data Models

Both tables reference `leads.lead_id`. The ORM declares cascading deletion for the foreign keys. `LeadScore` also has a unique constraint on `lead_id`, supporting one current score card per lead.

### `outreach_campaigns`

| Attribute | SQLAlchemy type | Key / behavior |
|---|---|---|
| `campaign_id` | Integer | Primary key; auto-increment |
| `lead_id` | Integer | Foreign key to `leads.lead_id`; indexed |
| `email_subject` | String | Required |
| `email_content` | Text | Required |
| `follow_up_strategy` | Text | Required |
| `tone` | String | Required; defaults to `professional` |
| `created_at` | DateTime with timezone | Required; defaults to current time |

### `lead_scores`

| Attribute | SQLAlchemy type | Key / behavior |
|---|---|---|
| `score_id` | Integer | Primary key; auto-increment |
| `lead_id` | Integer | Foreign key to `leads.lead_id`; indexed and unique |
| `lead_score` | Integer | Required; indexed; API schema validates 0–100 |
| `conversion_probability` | Float | Required; API schema validates 0.0–1.0 |
| `priority_level` | String | Required; indexed; schema allows `high`, `medium`, or `low` |
| `scoring_factors` | JSON | Required; stores factor details |
| `calculated_at` | DateTime with timezone | Required; defaults to current time |

## 5. Integration, Testing & Milestone Readiness

The repository contains integration tests for the health endpoint, outreach generation and history, scoring persistence and retrieval, missing-lead responses, and invalid scoring-service output. Tests use a temporary SQLite database with FastAPI dependency overrides.

### Test execution status

**Outreach generation and history:**   Ran the dedicated integration test for draft creation, persistence, and history retrieval:

```text
.venv/bin/python -m pytest -q tests/test_intelligence.py::test_outreach_generation_and_history
.                                                                        [100%]
1 passed, 1 warning in 0.41s
```

The test verifies that `POST /intelligence/outreach` returns a created campaign with generated subject, content, follow-up strategy, tone, and lead ID; that the campaign is persisted; and that `GET /intelligence/outreach/{lead_id}` returns the saved campaign in its history. The test passed. It does not cover editing or sending email.

**Focused Milestone 2 run:**  Executed `tests/test_intelligence.py`, which exercises outreach generation and history, missing-lead handling, score creation and upsert, score retrieval, invalid scoring-service output, and the health endpoint. Tests use a temporary SQLite database with FastAPI dependency overrides.

```text
.venv/bin/python -m pytest -q tests/test_intelligence.py
.......                                                                  [100%]
7 passed, 1 warning in 0.59s
```

**Result:** All seven focused tests passed; no test failures.
