# User Acceptance Test Plan

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Application:** SalesGenie AI - backend API and data layer
**Execution result:** [`uat-results.md`](uat-results.md)

---

## 1. Purpose

UAT answers a different question from the automated suite: *can a user complete the
workflows the SRS describes, against the application as it actually runs?* The automated
suite runs the app in-process. UAT runs it over real HTTP against a real PostgreSQL
database.

---

## 2. Scope and limitation

**In scope:** every workflow reachable through the API, for all six modules plus
authentication and role-based access.

**Out of scope:** anything that requires the Streamlit interface. The frontend has not been
delivered, so the five workflows that are purely visual (FR-006, FR-017, FR-023, FR-027,
FR-033, FR-044, FR-050, FR-051) cannot be accepted by a user yet. They are marked `BLOCKED`
in the traceability matrix rather than accepted on the strength of an API response.

This is stated plainly because a UAT report that claims a UI works when no UI exists is
worthless.

---

## 3. Personas

| Persona | Role in the system | What they must be able to do |
|---|---|---|
| Sales representative | `rep` | Create and edit prospects, import a CSV, analyse a company, generate and edit outreach, score a lead, log a call |
| Sales manager | `manager` | Everything a rep can do, plus delete prospects and take analytics snapshots |
| Sales operations / admin | `admin` | Everything above, plus create and deactivate users and change roles |
| Read-only stakeholder | `viewer` | Read prospects, scores and analytics; never write |

---

## 4. Test environment

| Item | Value |
|---|---|
| API | Uvicorn on `http://127.0.0.1:8011` |
| Database | PostgreSQL 16.15, database `salesgenie_uat`, isolated cluster on port 55432 |
| AI backend | `heuristic` (default, offline) |
| Auth | Enabled, JWT |
| Client | `scripts/qa_uat.py` (httpx) |

### 4.1 Setup procedure

```powershell
# 1. Create an empty database
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -p 55432 -U postgres -h 127.0.0.1 `
  -c "CREATE DATABASE salesgenie_uat;"

# 2. Apply the schema
$env:JWT_SECRET  = "<a local test secret>"
$env:DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_uat"
$env:AUTH_ENABLED = "true"
python -m alembic upgrade head

# 3. Create the administrator
python -m backend.cli create-user --email qa.admin@example.com --role admin `
  --full-name "QA Administrator" --password "<a local test password>"

# 4. Start the API
python -m uvicorn main:app --host 127.0.0.1 --port 8011

# 5. Run the acceptance workflows
python scripts/qa_uat.py --base-url http://127.0.0.1:8011 `
  --email qa.admin@example.com --password "<the same test password>"
```

Step 2 was executed as `downgrade base` followed by `upgrade head` during the recorded run,
which also proves the migration is reversible.

---

## 5. Workflows and acceptance criteria

Each workflow is a user story with a pass condition. The identifier is the one printed by
the runner.

| ID | Persona | Workflow | Pass condition | Requirement |
|---|---|---|---|---|
| UAT-01 | any | Open the application and check readiness | Health reports `status: ok`, database `ok`, AI `ok` | NFR-011 |
| UAT-02 | admin | Sign in | A token is issued and `/me` returns the admin profile | FR-001 / D-04 |
| UAT-03 | any | Sign in with a wrong password | Refused with `401 invalid_credentials`, no token | NFR-005 |
| UAT-04 | anonymous | Call a business endpoint without a token | Refused with `401` | NFR-005 |
| UAT-05 | rep | Add a prospect by hand | `201`, e-mail and website normalised, stage stored | FR-001, FR-009 |
| UAT-06 | rep | Try to add the same prospect twice | `409` with the matching lead; duplicate-check says `true` | FR-008 |
| UAT-07 | rep | Browse, search and page through prospects | Bare array, `X-Total-Count`/`X-Page`/`X-Page-Size`, search finds the new lead | FR-002 |
| UAT-08 | rep | Move a prospect to another stage | Stage changes and the derived status follows | FR-005 |
| UAT-09 | rep | Import a CSV containing two new rows and one duplicate | 2 imported, 1 duplicate reported, 3 total rows | FR-007, FR-008 |
| UAT-10 | rep | Submit an invalid prospect | `422` with field errors, nothing stored | AC-005 |
| UAT-11 | rep | Analyse a company | Needs, opportunities, qualification, missing information returned and stored | FR-011 to FR-016 |
| UAT-12 | rep | Generate outreach, edit it, open the history | Draft generated, edit accepted, history contains the campaign | FR-019 to FR-026 |
| UAT-13 | rep | Press Send | Refused with `501 email_transport_not_configured`; nothing sent | FR-024, AC-015 |
| UAT-14 | rep | Score a lead | 0-100 score, four factors summing to 100 points, `conversion_probability` null | FR-028 to FR-031 |
| UAT-15 | rep | Read the next-best-action | Action, reason, priority, timing and a follow-up draft | FR-032, AC-019 |
| UAT-16 | rep | Log a call and read the summary | Summary, key points and action items returned and stored | FR-036 to FR-039 |
| UAT-17 | rep | Attempt a CRM sync | `501 crm_not_configured`, a failure row in the sync log, lead still present | FR-043, FR-045 |
| UAT-18 | manager | Open the dashboard data | Conversion rate has a value; the three undefined KPIs are `null` + `pending_definition` | FR-046 to FR-050 |
| UAT-19 | manager | Open the follow-up panel data | Well-formed list of scored, non-terminal leads | FR-052 |
| UAT-20 | admin | Create a viewer and act as that viewer | Admin creates the user; viewer can read; viewer write is `403`; viewer cannot administer users | NFR-005 |
| UAT-21 | manager | Delete a prospect | `204`, then `404` on read | FR-004 |

---

## 6. Acceptance rules

1. A workflow passes only if every assertion in its row holds.
2. A workflow passes only if the evidence line is written to
   `docs/qa/evidence/`.
3. A workflow that reveals a partial requirement is reported as `PARTIAL` and linked to a
   defect. It is not rounded up to a pass.
4. A workflow that cannot run because a dependency is missing is `BLOCKED` with the reason.
5. The run is accepted when there are zero `FAIL` results and every `PARTIAL` has a defect
   reference.

---

## 7. Exit criteria

| Criterion | Target | Result |
|---|---|---|
| Workflows executed | 21 of 21 | Met |
| Workflows failed | 0 | Met |
| Partials documented with a defect | All | Met - UAT-15 → BUG-006 |
| Evidence written | Markdown and JSON | Met |
| Business-critical workflows (create, analyse, generate, score, delete) | All pass | Met |

---

## 8. Risks to acceptance

| Risk | Effect on UAT | Mitigation |
|---|---|---|
| No frontend | 8 requirements cannot be user-accepted | Documented as `BLOCKED`; API data verified so the frontend work is de-risked |
| External AI package absent | UAT runs on the heuristic engine only | Adapter proven against a stub; gate script ready |
| CRM and e-mail providers unconfigured | Those workflows test refusal, not delivery | Explicitly in scope as "must refuse visibly" |
| Schema still provisional | A later merge may invalidate stored data | UAT is re-run after the schema merge |
