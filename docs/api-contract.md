# API Contract

**Base URL (local):** `http://127.0.0.1:8000`
**Prefix:** `/api/v1`
**OpenAPI:** `GET /openapi.json`, interactive docs at `/docs`
**Version:** 1.0.0

This contract is the integration surface for Maheksaba's Streamlit frontend. It is stable for the
milestone; additive changes (new fields/endpoints) are allowed, breaking changes require a version
bump.

---

## 1. Conventions

### 1.1 Authentication

OAuth2 password flow. Send the credentials as `application/x-www-form-urlencoded`:

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=lead@example.com&password=...
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

Send `Authorization: Bearer <token>` on every other endpoint. Tokens are HS256 JWTs signed with
`JWT_SECRET`; the default lifetime is 120 minutes (`ACCESS_TOKEN_MINUTES`).

`GET /api/v1/health` is public. Everything else requires a valid token.

### 1.2 Roles

| Role | Read | Create/update business data | Delete leads | Manage users | Analytics snapshot |
|---|---|---|---|---|---|
| `admin` | yes | yes | yes | yes | yes |
| `manager` | yes | yes | yes | no | yes |
| `rep` | yes | yes | no | no | no |
| `viewer` | yes | no | no | no | no |

`AUTH_ENABLED=false` is a documented local-development escape hatch; it is never set in the
provided Docker configuration.

### 1.3 Error envelope

Every error has the same shape:

```json
{
  "detail": "Human readable message.",
  "code": "machine_readable_code",
  "meta": null
}
```

Request-validation errors (`422`) additionally include:

```json
{
  "detail": "Request validation failed.",
  "code": "validation_error",
  "meta": null,
  "errors": [
    {"loc": ["body", "company_name"], "msg": "String should have at least 1 character", "type": "string_too_short"}
  ]
}
```

Common codes: `not_authenticated`, `forbidden`, `lead_not_found`, `duplicate_lead`,
`invalid_stage`, `invalid_csv`, `file_too_large`, `unsupported_file_type`, `ai_unavailable`,
`ai_failed`, `score_not_found`, `campaign_not_found`, `crm_not_configured`,
`email_transport_not_configured`.

### 1.4 Pagination

List endpoints return a **plain JSON array** and expose pagination in response headers:

```
X-Total-Count: 137
X-Page: 2
X-Page-Size: 50
```

`page` is 1-based; `page_size` defaults to `DEFAULT_PAGE_SIZE` (50) and is capped at
`MAX_PAGE_SIZE` (500). A larger value returns `422 page_size_too_large`.

### 1.5 Lead representation

```json
{
  "id": "42",
  "company_name": "Acme Systems",
  "industry": "Software",
  "contact_name": "Dana Scully",
  "email": "dana@acme.test",
  "phone": "",
  "website": "https://acme.test",
  "company_size": "51-200",
  "annual_revenue": "",
  "funding_stage": "",
  "tech_stack": "",
  "company_description": "A growing B2B software company.",
  "prospect_role": "VP Sales",
  "engagement_history": "Meeting booked",
  "explicit_needs": "Reduce manual reporting.",
  "response_behavior": "",
  "user_research": "",
  "pain_points": "",
  "lead_source": "",
  "stage": "qualified",
  "status": "Active",
  "owner_id": 3,
  "created_at": "2026-10-26T09:15:00+00:00",
  "updated_at": "2026-10-26T09:15:00+00:00"
}
```

* `id` is serialised as a **string** for frontend compatibility.
* `stage` is the canonical lifecycle value: `prospecting`, `discovery`, `qualified`, `proposal`,
  `negotiation`, `converted`, `lost`.
* Input aliases are accepted (`New`, `Contacted`, `Closed Won`, `Closed Lost`, `Won`, ...) and
  normalised.
* `status` is **derived, read-only** presentation data: `New` (prospecting/discovery),
  `Active` (qualified/proposal/negotiation), `Closed` (converted/lost).
* `owner_id` is the creating user, or `null` when auth is disabled.

---

## 2. Authentication endpoints

### `POST /api/v1/auth/token`

| Field | Type | Required |
|---|---|---|
| `username` | string (e-mail) | yes |
| `password` | string | yes |

`200` -> token response. `401 invalid_credentials` for a wrong password, unknown user or inactive
account. Response timing is equalised with a dummy hash so account existence is not leaked.

### `GET /api/v1/auth/me`

`200` -> `UserRead` (`id`, `email`, `full_name`, `role`, `is_active`, `created_at`).

### `GET /api/v1/auth/users` (admin)

`200` -> array of `UserRead`.

### `POST /api/v1/auth/users` (admin)

```json
{"email": "rep@example.com", "full_name": "Rep", "password": "min-8-chars", "role": "rep"}
```

`201` -> `UserRead`. `409 user_exists`. Passwords are stored as PBKDF2-HMAC-SHA256; the hash is
never returned.

### `PATCH /api/v1/auth/users/{user_id}` (admin)

```json
{"role": "manager", "is_active": false, "full_name": "New Name"}
```

`200` -> `UserRead`. `422 invalid_role`.

---

## 3. Lead endpoints (Module 1)

### `POST /api/v1/leads`

Required: `company_name` (1-240 chars, whitespace-normalised).

Optional lead fields (all strings): `industry` (160), `contact_name` (200), `email` (320, validated,
lower-cased), `phone` (80), `website` (500, `https://` added if no scheme), `company_size` (100),
`annual_revenue` (100), `funding_stage` (100), `tech_stack` (4000), `company_description` (8000),
`prospect_role` (120), `engagement_history` (8000), `explicit_needs` (8000),
`response_behavior` (4000), `user_research` (8000), `pain_points` (8000), `lead_source` (120).

Lifecycle: `stage` (canonical or alias) or legacy `status`.

`201` -> `LeadRead`.

| Status | Code | Cause |
|---|---|---|
| 422 | `validation_error` | Missing company name, invalid e-mail/URL, over-length field, invalid stage |
| 409 | `duplicate_lead` | Duplicate e-mail, or same company + contact name |

Duplicate response:

```json
{
  "detail": "A lead with the same identity already exists.",
  "code": "duplicate_lead",
  "meta": {"matched_lead_id": "7", "match_reason": "email"}
}
```

**Duplicate policy** (identical for create, update and CSV import):

1. A non-empty e-mail is authoritative (case-insensitive).
2. Without an e-mail, the same normalised company **and** contact name is a duplicate.

### `GET /api/v1/leads`

| Query | Type | Notes |
|---|---|---|
| `query` | string (200) | Case-insensitive search over company, contact, email, industry |
| `stage` | string | Canonical or alias; invalid -> `422 invalid_stage` |
| `industry` | string | Exact, case-insensitive |
| `page` | int >= 1 | Default 1 |
| `page_size` | int 1-500 | Default 50 |

`200` -> array of `LeadRead`, newest first, with pagination headers.

### `GET /api/v1/leads/{lead_id}`

`200` -> `LeadRead`; `404 lead_not_found`.

### `PATCH /api/v1/leads/{lead_id}`

Partial update. Only supplied fields change. `stage`/`status` accepted. Re-runs duplicate
detection when e-mail, company or contact changes. `200` -> `LeadRead`; `404`; `409`.

### `DELETE /api/v1/leads/{lead_id}` (manager/admin)

`204` with no body. Child rows are removed by `ON DELETE CASCADE`; CRM logs are retained with
`lead_id = NULL`. `403 forbidden` for `rep`/`viewer`.

### `POST /api/v1/leads/duplicate-check`

```json
{"email": "dana@acme.test", "company_name": "", "contact_name": ""}
```

`200`:

```json
{"is_duplicate": true, "matched_lead_id": "42", "match_reason": "email"}
```

### `POST /api/v1/leads/import`

`multipart/form-data` with one `file` part, `.csv`, UTF-8 (BOM tolerated), maximum
`MAX_CSV_BYTES` (5 MB) and `MAX_CSV_ROWS` (5000).

Accepted header aliases include `company`/`company name`/`account`, `email address`,
`contact name`/`full name`, `phone`/`mobile`, `website`/`url`, `industry`/`sector`,
`company size`/`employees`, `role`/`title`, `needs`, `pain points`, `source`, `stage`/`status`.

`200` -> `ImportReport`:

```json
{
  "filename": "leads.csv",
  "imported": 8,
  "duplicates": 2,
  "invalid": 1,
  "skipped": 3,
  "total_rows": 11,
  "errors": [
    {"row": 4, "error": "email is not a valid address"},
    {"row": 7, "error": "email already belongs to lead 12"}
  ],
  "duplicate_rows": [7, 9]
}
```

Row numbers are 1-based including the header (data starts at row 2). Every row is written inside a
savepoint, so one bad row never discards previously imported rows. The report is capped at 200
error entries.

| Status | Code | Cause |
|---|---|---|
| 415 | `unsupported_file_type` | Extension is not `.csv` |
| 413 | `file_too_large` | Over the byte limit |
| 422 | `empty_file` | No content |
| 422 | `invalid_csv` | Not UTF-8, no header, no company column, over row limit |

---

## 4. Company analysis / lead intelligence (Module 2)

### `POST /api/v1/leads/{lead_id}/insights`

Body optional:

```json
{"product_service": "SalesGenie AI", "extra_context": "Met at a conference."}
```

Runs the configured intelligence engine, validates the structured result, persists it to
`company_insights`, and returns it.

`200`:

```json
{
  "id": 5,
  "lead_id": 42,
  "created_at": "2026-10-26T09:20:00+00:00",
  "execution": {"engine": "heuristic", "provider": "heuristic", "model": "deterministic-heuristic-v1", "duration_ms": 3, "used_mock": true, "fallback_reason": null},
  "company_overview": "... No website retrieval or external research was performed.",
  "supported_facts": [{"statement": "Industry: Software", "source": "Supplied lead record", "source_type": "backend", "confidence": "high"}],
  "potential_challenges": [{"statement": "...", "rationale": "...", "confidence": "low", "requires_validation": true}],
  "possible_needs": [],
  "opportunities": [],
  "product_industry_fit": "...",
  "buyer_role_relevance": "...",
  "qualification_insights": ["..."],
  "discovery_questions": ["..."],
  "missing_information": ["Website or retrieved company material"],
  "qualification": {
    "category": "Qualified",
    "fit_assessment": "...",
    "buyer_relevance": "...",
    "engagement_assessment": "...",
    "positive_signals": [],
    "risks_or_gaps": [],
    "recommended_next_step": "...",
    "confidence": "medium"
  },
  "confidence": "medium",
  "disclaimer": "No website or external company research was performed; conclusions use only supplied context."
}
```

| Status | Code | Cause |
|---|---|---|
| 404 | `lead_not_found` | Unknown lead |
| 502 | `ai_failed` | Engine raised or returned invalid output |
| 503 | `ai_unavailable` | Configured engine cannot be constructed |

### `GET /api/v1/leads/{lead_id}/insights`

`200` -> array of persisted insights, newest first. Each row contains `id`, `lead_id`,
`business_needs`, `opportunities`, `pain_points`, `industry_context`, `qualification`,
`recommended_value_proposition`, `discovery_questions`, `missing_information`,
`supporting_evidence`, `provider`, `model`, `created_at`.

> Note: the persisted row shape is normalised for storage; the POST response is the richer
> contract shape. A frontend that needs the rich shape should use the POST response.

---

## 5. Outreach (Module 3)

### `POST /api/v1/outreach/generate`

```json
{
  "lead_id": 42,
  "tone": "professional",
  "length": "medium",
  "outreach_type": "cold_email",
  "goal": "book a discovery call",
  "industry": "Software",
  "pain_points": ["manual reporting"],
  "product_service": "SalesGenie AI",
  "call_to_action": "Would a short call help?"
}
```

| Field | Allowed |
|---|---|
| `tone` | free string, max 60 (e.g. professional, formal, friendly, direct) |
| `length` | `short`, `medium`, `long` |
| `outreach_type` | `cold_email`, `follow_up`, `linkedin_message`, `call_script`, `short_message` |
| `pain_points` | up to 10, each truncated to 300 chars |
| `goal` | max 200 |
| `product_service` | max 500 |
| `call_to_action` | max 500 |

> **Engine note.** With the default `heuristic` engine every parameter above is honoured. With
> `SALES_GENIE_AI_BACKEND=external`, `length` is ignored because the reviewed AI package has no
> length control; `outreach_type`, `goal` and `pain_points` are translated to that package's
> `channel`, `campaign_objective` and `company_insights`. See `docs/ai-review.md` A-11.

Generates content, persists a `draft` campaign, returns:

```json
{
  "id": 9,
  "lead_id": 42,
  "status": "draft",
  "execution": {"engine": "heuristic", "provider": "heuristic", "model": "deterministic-heuristic-v1", "duration_ms": 2, "used_mock": true},
  "channel": "Email",
  "subject_line": "A question about Acme Systems' priorities",
  "body": "Hi Dana, ...",
  "call_to_action": "Would a short call help?",
  "personalization_rationale": ["..."],
  "facts_used": [{"statement": "Industry: Software", "...": "..."}],
  "assumptions": [],
  "missing_context": ["Buying timing"],
  "alternative_angle": "..."
}
```

`404 lead_not_found`; `422 validation_error`; `502 ai_failed`; `503 ai_unavailable`.

### `POST /api/v1/outreach/send`

**Always returns `501 email_transport_not_configured`.** No e-mail transport exists in this build
(SRS D-05). The endpoint exists so a future transport has a stable path, and so the frontend cannot
mistake generation for delivery.

### `GET /api/v1/leads/{lead_id}/outreach-drafts`

`200` -> array of `OutreachCampaignRead`:

```json
{
  "id": 9, "lead_id": 42, "subject": "...", "body": "...", "channel": "Email",
  "tone": "professional", "length": "medium", "outreach_type": "cold_email",
  "goal": "...", "industry_context": "Software", "pain_points_used": ["manual reporting"],
  "status": "draft", "provider": "heuristic", "model": "deterministic-heuristic-v1",
  "created_at": "...", "updated_at": "..."
}
```

### `POST /api/v1/leads/{lead_id}/outreach-drafts`

Save a user-edited draft:

```json
{"subject": "Edited", "body": "Edited body.", "tone": "friendly", "status": "draft"}
```

`201` -> `OutreachCampaignRead`. `status` is one of `draft`, `approved`, `sent`, `archived`.
The record is marked `provider = "user-supplied"`.

### `GET /api/v1/outreach/campaigns/{campaign_id}`

`200` -> `OutreachCampaignRead`; `404 campaign_not_found`.

### `PATCH /api/v1/outreach/campaigns/{campaign_id}`

Same body as the save endpoint. `200` -> `OutreachCampaignRead`.

### `POST /api/v1/outreach/campaigns/{campaign_id}/mark-sent`

Records that the user sent the message through an external tool. It does **not** transmit e-mail.
`200` -> campaign with `status = "sent"`.

---

## 6. Lead scoring (Module 4)

### `POST /api/v1/leads/{lead_id}/scores`

No body. Runs the configured engine, persists an append-only score row, returns:

```json
{
  "id": 15,
  "lead_id": 42,
  "score": 87,
  "qualification_category": "Qualified",
  "conversion_probability": null,
  "priority_level": "hot",
  "factors": [
    {"name": "Company fit", "weight": 30.0, "normalized_value": 1.0, "points": 30.0, "explanation": "Signals present: ...", "signal": "positive"},
    {"name": "Intent", "weight": 25.0, "normalized_value": 0.6, "points": 15.0, "explanation": "...", "signal": "positive"},
    {"name": "Engagement", "weight": 25.0, "normalized_value": 1.0, "points": 25.0, "explanation": "...", "signal": "positive"},
    {"name": "Decision readiness", "weight": 20.0, "normalized_value": 0.85, "points": 17.0, "explanation": "...", "signal": "positive"}
  ],
  "positive_signals": ["..."],
  "negative_signals": [],
  "missing_information": [],
  "recommended_next_action": "Schedule a discovery conversation ...",
  "explanation": "No calibrated conversion model is configured. ...",
  "model_version": "heuristic:deterministic-heuristic-v1",
  "created_at": "2026-10-26T09:25:00+00:00",
  "execution": {"engine": "heuristic", "provider": "heuristic", "model": "deterministic-heuristic-v1", "duration_ms": 1, "used_mock": true},
  "probability_band": "high",
  "probability_note": "No calibrated conversion model is configured. The band is an uncalibrated heuristic and must not be read as a statistical probability.",
  "methodology_note": "Configurable heuristic score derived from engagement, fit, intent and decision readiness. Not a trained or calibrated predictive model."
}
```

**Contract guarantees:**

* `score` is an integer 0-100.
* `factors` always sums to 100 weight.
* `conversion_probability` is `null` unless a calibrated model is configured. Do not display it as
  a percentage when it is null.
* `probability_band` is explicitly uncalibrated.
* Scores are append-only; re-scoring adds a row.

`404 lead_not_found`; `502 ai_failed`; `503 ai_unavailable`.

### `GET /api/v1/leads/{lead_id}/scores`

`200` -> array of score payloads (without the `execution` block), newest first.

### `GET /api/v1/leads/{lead_id}/scores/latest`

`200` -> the newest score; `404 score_not_found` if never scored.

---

## 7. Conversation intelligence (Module 5, local half)

### `POST /api/v1/conversations/summarize`

```json
{
  "lead_id": 42,
  "transcript": "Dana said reporting is manual. Dana will send the spreadsheet by Friday.",
  "notes": "",
  "interaction_type": "call"
}
```

At least one of `transcript`/`notes` must be non-empty; `interaction_type` is `call`, `meeting`,
`demo`, `email` or `note`.

`200` -> summary plus persisted interaction id:

```json
{
  "id": 3,
  "lead_id": 42,
  "created_at": "...",
  "execution": {"...": "..."},
  "executive_summary": "...",
  "key_discussion_points": ["..."],
  "customer_requirements": [],
  "pain_points": ["..."],
  "objections": [],
  "product_interests": [],
  "buying_signals": [],
  "competitor_mentions": [],
  "decisions_and_commitments": [],
  "action_items": [{"action": "Dana will send the spreadsheet by Friday.", "owner": "Dana", "due_date": null, "evidence": "...", "confidence": "high"}],
  "suggested_follow_up": "...",
  "missing_or_uncertain": [],
  "source_note": "Extracted only from the supplied transcript and notes."
}
```

The engine never invents owners, dates or commitments. Absent items are listed in
`missing_or_uncertain`.

`404 lead_not_found`; `422 validation_error`; `502`/`503` as above.

### `POST /api/v1/leads/{lead_id}/conversations`

Persist a summary produced elsewhere (for example an edited summary):

```json
{
  "interaction_type": "call",
  "transcript": "...",
  "summary": {
    "executive_summary": "...",
    "key_discussion_points": ["..."],
    "action_items": [{"action": "...", "evidence": "..."}]
  }
}
```

`201` -> `ConversationRead`. `422 empty_summary` when `summary.executive_summary` is empty.

### `GET /api/v1/leads/{lead_id}/conversations`

`200` -> array of `ConversationRead` (`id`, `lead_id`, `interaction_type`, `interaction_date`,
`transcript`, `summary`, `key_points`, `action_items`), newest first.

### `GET /api/v1/conversations/{interaction_id}`

`200` -> `ConversationRead`; `404 interaction_not_found`.

---

## 8. Analytics and follow-ups (Module 6)

### `GET /api/v1/analytics`

`200`:

```json
{
  "source": "database",
  "is_demo": false,
  "generated_at": "...",
  "total_leads": 12,
  "qualified_leads": 4,
  "converted_leads": 1,
  "average_lead_score": 68.5,
  "conversion_rate": {"value": 0.0833, "definition": "converted_leads / total_leads ... Proposed definition for SRS D-10 - pending team approval.", "pending_definition": false},
  "pipeline_value": {"value": null, "definition": "No field in the current schema supports this metric; SRS D-10 is unresolved.", "pending_definition": true},
  "average_response_time_days": {"value": null, "definition": "...", "pending_definition": true},
  "average_sales_cycle_days": {"value": null, "definition": "...", "pending_definition": true},
  "outreach_activity": 9,
  "interactions_logged": 3,
  "pipeline_distribution": [{"stage": "prospecting", "count": 5}, "... 7 stages"],
  "lead_score_distribution": [{"band": "0-44", "count": 2}, {"band": "45-69", "count": 4}, {"band": "70-100", "count": 3}],
  "activity_trend": [{"date": "2026-10-13", "activity": 0}, "... 14 days"],
  "follow_up_tasks": 2
}
```

Rules:

* `qualified_leads` counts `qualified`, `proposal`, `negotiation`.
* `average_lead_score` uses the latest score per lead.
* `conversion_rate` uses the proposed D-10 definition and says so in `definition`.
* Metrics the schema cannot support are `null` with `pending_definition: true`. The frontend must
  render them as "Not defined", never as zero.

### `POST /api/v1/analytics/insights`

Runs the intelligence engine over the current aggregates. `200`:

```json
{
  "execution": {"...": "..."},
  "insights": [{"title": "Largest pipeline segment", "observation": "prospecting contains 5 leads.", "evidence": "Backend-supplied pipeline distribution.", "confidence": "high"}],
  "caveat": "Observations describe supplied aggregates only; they do not establish causes or forecast results."
}
```

### `POST /api/v1/analytics/snapshot` (manager/admin)

Persists the current aggregate to `sales_analytics`. `201` -> `{"id": 1, "metric_date": "..."}`.
`403 forbidden` for `rep`/`viewer`.

### `GET /api/v1/follow-ups`

Derived from the **latest stored score** per non-terminal lead, highest score first, max 20:

```json
{
  "lead_id": "42",
  "company_name": "Acme Systems",
  "priority": "hot",
  "recommended_action": "Schedule a discovery conversation ...",
  "score": 87,
  "last_interaction_at": null,
  "reason": "Latest stored score 87/100 (heuristic:deterministic-heuristic-v1)."
}
```

Leads must be scored first. `PATCH /api/v1/follow-ups/{id}` is **not implemented**: there is no
recommendations table in the canonical schema. Adding one requires an SRS decision.

### `GET /api/v1/recommendations/{lead_id}`

Runs the engine for one lead. `200`:

```json
{
  "execution": {"...": "..."},
  "lead_id": "42",
  "related_lead": "Acme Systems",
  "recommended_action": "...",
  "reason": "...",
  "supporting_evidence": [{"statement": "...", "source": "Lead record", "source_type": "backend", "confidence": "medium"}],
  "priority": "High",
  "suggested_timing": "Within one business day",
  "status": "Open",
  "follow_up_draft": "..."
}
```

---

## 9. CRM surface (Module 5, planned transport - SRS D-06)

| Endpoint | Behaviour |
|---|---|
| `GET /crm/providers` | `[{"provider":"salesforce","configured":false,"live_sync_available":false}, ...]` |
| `POST /crm/mappings/validate` | Validates target fields against the lead contract; never persists |
| `POST /crm/sync/preview` | Dry run; returns each lead's export payload or an error |
| `POST /crm/sync` | Records a failed `crm_sync_logs` row and returns `501 crm_not_configured` with `meta.sync_log_id` |
| `GET /crm/sync-logs` | Last 250 attempts |
| `POST /crm/sync-logs/{id}/retry` | Increments `attempt_count`, records that transport is unavailable; `409` if already successful |

No CRM credentials are used because no transport is implemented. `SALESFORCE_ACCESS_TOKEN` and
`HUBSPOT_ACCESS_TOKEN` are read only to report `configured` state.

---

## 10. System endpoints

### `GET /api/v1/health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "ok",
  "database_dialect": "postgresql",
  "auth_enabled": true,
  "ai_backend": "heuristic",
  "ai_status": "ok"
}
```

`status` becomes `degraded` when the database ping fails. `GET /health` is an alias outside the
documented schema. `GET /` returns the service name and links.

---

## 11. Hidden compatibility aliases

These paths exist for the earlier draft frontend but are excluded from OpenAPI to keep the
documented surface clean:

| Alias | Equivalent |
|---|---|
| `POST /api/v1/intelligence/analyze/{lead_id}` | `POST /api/v1/leads/{lead_id}/insights` |
| `GET /api/v1/intelligence/{lead_id}` | `GET /api/v1/leads/{lead_id}/insights` |
| `POST /api/v1/scoring/{lead_id}` | `POST /api/v1/leads/{lead_id}/scores` |
| `GET /api/v1/scoring/{lead_id}` | `GET /api/v1/leads/{lead_id}/scores` |
| `GET /api/v1/outreach/{lead_id}` | `GET /api/v1/leads/{lead_id}/outreach-drafts` |
| `GET /api/v1/dashboard/summary` | `GET /api/v1/analytics` |

Prefer the documented paths; aliases may be removed in a future version.

---

## 12. Database side effects

| Endpoint | Writes |
|---|---|
| `POST /leads` | `leads` |
| `PATCH /leads/{id}` | `leads` |
| `DELETE /leads/{id}` | deletes `leads`; cascades children; sets `crm_sync_logs.lead_id = NULL` |
| `POST /leads/import` | `leads` (one savepoint per row, one commit at the end) |
| `POST /leads/{id}/insights` | `company_insights` |
| `POST /outreach/generate` | `outreach_campaigns` (draft) |
| `POST /leads/{id}/outreach-drafts` | `outreach_campaigns` |
| `PATCH /outreach/campaigns/{id}` | `outreach_campaigns` |
| `mark-sent` | `outreach_campaigns.status` |
| `POST /leads/{id}/scores` | `lead_scores` (append-only) |
| `POST /conversations/summarize` | `sales_interactions` |
| `POST /leads/{id}/conversations` | `sales_interactions` |
| `POST /analytics/snapshot` | `sales_analytics` |
| `POST /crm/sync` | `crm_sync_logs` (failed attempt) |
| `POST /crm/sync-logs/{id}/retry` | `crm_sync_logs` |
| Auth endpoints | `users` |

Read-only endpoints never write.

---

## 13. AI-service dependencies

| Endpoint | Needs the intelligence engine |
|---|---|
| `POST /leads/{id}/insights` | yes |
| `POST /outreach/generate` | yes |
| `POST /leads/{id}/scores` | yes |
| `POST /conversations/summarize` | yes |
| `POST /analytics/insights` | yes |
| `GET /recommendations/{lead_id}` | yes |
| `GET /follow-ups` | no - derived from stored scores |
| `GET /analytics` | no |
| all lead/import/CRM endpoints | no |

With the default `heuristic` engine, none of these require network access or credentials.
