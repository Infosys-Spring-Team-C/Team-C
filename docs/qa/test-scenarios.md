# Test Scenarios and Acceptance Criteria

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Reference:** [`../SRS.md`](../SRS.md) acceptance criteria `AC-001` to `AC-030`

Each scenario states what is exercised, the precondition, the acceptance criteria taken
from the SRS, and the verdict from this test cycle. `TC-*` identifiers are expanded in
[`test-cases.md`](test-cases.md).

---

## Module 1 - Prospect management and database

### SCN-M1-01 - Create a prospect and find it again
*Precondition:* an authenticated user with a write role; empty database.
*Steps:* submit a complete prospect; list prospects; open the prospect detail.
*Acceptance:* `AC-001`, `AC-005`
*Verdict:* **PASS** - created with `201`, retrievable by id and in the list, e-mail and
website normalised. Evidence: `TC-M1-001`, `TC-M1-003`, UAT-05.

### SCN-M1-02 - Update and delete a prospect
*Precondition:* one stored prospect.
*Steps:* patch the stage and a free-text field; delete as a manager; read it again.
*Acceptance:* `AC-002`, `AC-004`
*Verdict:* **PASS** - `PATCH` returns the updated record, `DELETE` returns `204` and the
record then returns `404`. Evidence: `TC-M1-004`, `TC-M1-005`, UAT-08, UAT-21.

### SCN-M1-03 - Duplicate prevention on manual entry and import
*Precondition:* one stored prospect with a known e-mail.
*Steps:* submit the same e-mail again; run the duplicate-check endpoint; import a CSV
containing one row that collides with stored data.
*Acceptance:* `AC-003`, `AC-005`
*Verdict:* **PASS** - `409` with the matching lead, `is_duplicate: true`, and the import
report separates `imported`, `duplicates` and `invalid`. Evidence: `TC-M1-007`,
`TC-M1-008`, UAT-06, UAT-09.

### SCN-M1-04 - Lifecycle stages
*Precondition:* one stored prospect.
*Steps:* create with a valid stage; create with an invalid stage; move between stages;
filter the list by stage.
*Acceptance:* `AC-004`, `AC-005`
*Verdict:* **PASS** - the seven canonical stages are accepted, aliases normalise, unknown
values return `422`. Evidence: `TC-M1-006`.

### SCN-M1-05 - Persistence beyond a single request
*Precondition:* stored prospect.
*Steps:* read the record in a later request; read it through a separate database
connection.
*Acceptance:* `AC-001`
*Verdict:* **PARTIAL** - persistence across requests and connections is proven; a full
process-restart replay is `TC-E2E-002` and was not executed. See
[`test-cases.md`](test-cases.md).

---

## Module 2 - Lead intelligence

### SCN-M2-01 - Company analysis for a qualified prospect
*Precondition:* a prospect with industry, description, size, needs and engagement.
*Steps:* request analysis; inspect the structured output; re-read stored insights.
*Acceptance:* `AC-006`, `AC-007`, `AC-008`
*Verdict:* **PASS** - business needs, opportunities, industry context, qualification and
discovery questions are returned and persisted. Evidence: `TC-M2-001` to `TC-M2-003`,
UAT-11.

### SCN-M2-02 - Missing context is declared, not invented
*Precondition:* a prospect with almost no context.
*Steps:* request analysis.
*Acceptance:* `AC-006`, `AC-010`
*Verdict:* **PASS** - `missing_information` is populated and the disclaimer states that no
external research was performed. Evidence: `TC-M2-007`.

### SCN-M2-03 - Invalid AI output is rejected
*Precondition:* an engine stub returning a malformed payload.
*Steps:* call analysis; assert the response is an error and nothing is persisted.
*Acceptance:* `AC-010`
*Verdict:* **PASS** - invalid package output raises `IntelligenceError` and the API returns
`502 ai_failed`. Evidence: `TC-M2-005`.

### SCN-M2-04 - Provider unavailable
*Precondition:* `SALES_GENIE_AI_BACKEND=external` with the package absent.
*Steps:* start the app; call health; call analysis.
*Acceptance:* `AC-009`
*Verdict:* **PASS** - health reports `ai_status: unavailable: ...` and analysis returns a
clear error without touching stored data. Evidence: `TC-M2-006`.

---

## Module 3 - Outreach generation

### SCN-M3-01 - Generate with the six SRS inputs
*Precondition:* a prospect with pain points and industry.
*Steps:* generate with tone, length, outreach type, goal, pain points and industry.
*Acceptance:* `AC-011`, `AC-012`
*Verdict:* **PASS** - all six inputs are accepted and materially change the draft
(channel mapping, tone and length alter the body). Evidence: `TC-M3-001`, `TC-M3-002`,
`TC-M3-003`, UAT-12.

### SCN-M3-02 - Edit a draft and retrieve history
*Precondition:* one generated campaign.
*Steps:* patch the body; list the lead's campaigns; open the campaign by id.
*Acceptance:* `AC-013`, `AC-014`
*Verdict:* **PASS** - the edit persists and history is returned newest first.
Evidence: `TC-M3-005`, `TC-M3-008`, UAT-12.

### SCN-M3-03 - Refresh produces a new variant
*Precondition:* one generated campaign.
*Steps:* generate again with the same inputs.
*Acceptance:* `AC-013`
*Verdict:* **NOT RUN** - generating again creates a second campaign, but no test asserts
that the new variant differs from the previous one. Tracked as a coverage gap, not a
defect.

### SCN-M3-04 - Send action is honest
*Precondition:* an authenticated writer.
*Steps:* call the send endpoint.
*Acceptance:* `AC-015`
*Verdict:* **PASS** - returns `501 email_transport_not_configured` with an explicit
message referencing D-05. Nothing is sent and no campaign is marked sent.
Evidence: `TC-M3-007`, UAT-13.

### SCN-M3-05 - No invented claims
*Precondition:* a prospect without pain points and without industry.
*Steps:* generate outreach.
*Acceptance:* `AC-011`, `AC-012`
*Verdict:* **PASS** - the draft declares the assumption and contains no industry-specific
claim. Evidence: `TC-M3-009`.

---

## Module 4 - Scoring and recommendations

### SCN-M4-01 - Explainable score on the 0-100 scale
*Precondition:* a prospect with rich context.
*Steps:* request a score; inspect the four factors, weights and points.
*Acceptance:* `AC-016`, `AC-017`
*Verdict:* **PASS** - score is bounded 0-100, the four SRS factors are present with
weights summing to 100 points, and the score equals the sum of factor points.
Evidence: `TC-M4-001`, `TC-M4-003`, UAT-14.

### SCN-M4-02 - Conversion probability is not faked
*Precondition:* default heuristic engine.
*Steps:* request a score; inspect `conversion_probability` and `probability_note`.
*Acceptance:* `AC-016`
*Verdict:* **PARTIAL** - `conversion_probability` is `null` and an explicit uncalibrated
band plus note is returned. FR-029 asks for an estimate; shipping a number from an
uncalibrated heuristic would be worse. Depends on SRS D-09/D-13. Evidence: `TC-M4-002`.

### SCN-M4-03 - Score history is append-only
*Precondition:* one lead scored twice.
*Steps:* score, score again, list history.
*Acceptance:* `AC-018`
*Verdict:* **PASS** - history grows, earlier scores are not mutated. Evidence: `TC-M4-004`.

### SCN-M4-04 - Degraded behaviour on missing data
*Precondition:* a prospect with only a company name.
*Steps:* request a score.
*Acceptance:* `AC-016`
*Verdict:* **PASS** - no exception; the score is low and `missing_information` explains
why. Evidence: `TC-M4-006`.

### SCN-M4-05 - Next-best-action recommendation
*Precondition:* a scored prospect.
*Steps:* request the recommendation.
*Acceptance:* `AC-019`
*Verdict:* **PASS** - timing, channel and content strategy are returned. The channel is
`email` when outreach is justified and `null` when it is not. BUG-006 closed. Evidence:
`TC-M4-005`, UAT-15, `test_recommendation_endpoint`.

### SCN-M4-06 - Accuracy against a labelled dataset
*Precondition:* an agreed test dataset and metric.
*Steps:* score the dataset and compare.
*Acceptance:* `AC-020`
*Verdict:* **BLOCKED** - SRS D-13 is unresolved; no metric and no dataset exist. Not
claimed.

---

## Module 5 - Conversations and CRM

### SCN-M5-01 - Summarise meeting notes
*Precondition:* a prospect and a call transcript.
*Steps:* submit the transcript; inspect summary, key points and action items; list stored
interactions.
*Acceptance:* `AC-021`, `AC-023`
*Verdict:* **PASS** - summary, discussion points and action items are produced and the
interaction is stored. Evidence: `TC-M5-001` to `TC-M5-004`, UAT-16.

### SCN-M5-02 - Empty notes are refused, nothing is fabricated
*Precondition:* a prospect.
*Steps:* submit empty notes; submit notes with no commitments.
*Acceptance:* `AC-022`
*Verdict:* **PASS** - empty input returns `422`; no commitment is invented when none is
stated. Evidence: `TC-M5-005`, `TC-M5-006`.

### SCN-M5-03 - CRM field mapping validation
*Precondition:* an authenticated user.
*Steps:* validate a valid mapping; validate an invalid one.
*Acceptance:* `AC-024`
*Verdict:* **PASS** - valid mappings are accepted, invalid ones are reported per field.
Evidence: `TC-M5-007`.

### SCN-M5-04 - CRM sync failure is safe and logged
*Precondition:* no CRM transport configured.
*Steps:* preview a sync; attempt a real sync; read sync logs; re-read the lead.
*Acceptance:* `AC-024`, `AC-025`
*Verdict:* **PASS** - preview is a dry run, the real sync returns `501 crm_not_configured`,
a failed attempt is written to the sync log, and the local record is untouched.
Evidence: `TC-M5-008`, `TC-M5-009`, UAT-17.

---

## Module 6 - Analytics dashboard

### SCN-M6-01 - Conversion rate is computed
*Precondition:* a database containing converted and unconverted leads.
*Steps:* request analytics.
*Acceptance:* `AC-026`, `AC-027`
*Verdict:* **PASS** - `conversion_rate` carries a value and a written definition.
Evidence: `TC-M6-001`, UAT-18.

### SCN-M6-02 - Undefined KPIs are withheld, not invented
*Precondition:* any dataset.
*Steps:* request analytics; inspect pipeline value, average response time and average
sales cycle.
*Acceptance:* `AC-026`
*Verdict:* **PASS** - all three return `value: null` with `pending_definition: true` while
SRS D-10 is open. Evidence: `TC-M6-002` to `TC-M6-004`, UAT-18.

### SCN-M6-03 - Empty dataset
*Precondition:* freshly migrated database with no leads.
*Steps:* request analytics and follow-ups.
*Acceptance:* `AC-030`
*Verdict:* **PASS** - both endpoints return well-formed empty results rather than errors.
Evidence: `TC-M6-007`.

### SCN-M6-04 - Dashboard rendering
*Precondition:* a Streamlit frontend.
*Steps:* open the dashboard; compare KPI cards and Kanban with the database.
*Acceptance:* `AC-026`, `AC-028`, `AC-029`, `AC-030`
*Verdict:* **PARTIAL** - the frontend now exists and the dashboard tab renders under
`AppTest` with 0 exceptions; the KPI cards and Kanban have not been visually compared with
the database in a human acceptance pass. Evidence:
`evidence/2026-10-27-frontend-apptest.txt`, `evidence/2026-10-27-browser-ui-check.txt`.

---

## Cross-cutting scenarios

### SCN-X-01 - Authentication and role-based access
*Acceptance:* `NFR-005`
*Verdict:* **PASS** - unauthenticated calls return `401`; a viewer can read but not write;
user administration is admin-only; expired and wrongly-signed tokens are rejected.
Evidence: `TC-SEC-001` to `TC-SEC-004`, UAT-02 to UAT-04, UAT-20.

### SCN-X-02 - Database integrity and migrations
*Acceptance:* `AC-001`, `AC-002`
*Verdict:* **PASS** - eight tables, expected keys and constraints, cascade behaviour, and a
successful Alembic upgrade **and downgrade** on PostgreSQL 16. Evidence: `TC-DB-001` to
`TC-DB-005`.

### SCN-X-03 - Deployment
*Acceptance:* `NFR-011`
*Verdict:* **PASS** - Docker 29.7.2 built both images and `docker compose up -d` brought up
`db`, `api` and `frontend`; all three health checks passed and the API migrated PostgreSQL.
BUG-012 closed. Evidence: `TC-DEP-001`, `TC-DEP-002`,
`evidence/2026-10-27-docker-compose-verification.txt`.

### SCN-X-04 - Performance against the 5-second target
*Acceptance:* `NFR-001`
*Verdict:* **NOT RUN** - SRS D-11 leaves the measurement conditions undefined. The UAT
runner records per-workflow durations, but they are not a benchmark and are not reported
as compliance.
