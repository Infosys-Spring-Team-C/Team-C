# User Acceptance Test Results

**Executed:** 26 October 2026, 13:50:27 UTC
**Operator:** Mohamed Isharak M (`qa.admin@example.com`)
**Target:** `http://127.0.0.1:8011`
**Database:** PostgreSQL 16.15, `salesgenie_uat` (freshly migrated)
**AI backend:** `heuristic` (offline, deterministic)
**Runner:** `scripts/qa_uat.py`

## Result: 20 passed, 1 partial, 0 failed

Raw evidence:
[`evidence/2026-10-26-uat-live-postgres-heuristic.md`](evidence/2026-10-26-uat-live-postgres-heuristic.md)
and the JSON equivalent.

---

## 1. Results

| ID | Workflow | Status | Observed | ms |
|---|---|---|---|---|
| UAT-01 | Health and readiness | PASS | `status: ok`, `database: ok`, `database_dialect: postgresql`, `ai_backend: heuristic`, `ai_status: ok`, `auth_enabled: true`, version `1.0.0` | 3 |
| UAT-02 | Administrator can sign in | PASS | Bearer token issued, `expires_in: 7200`; `/me` returned role `admin`, id 1 | 105 |
| UAT-03 | Wrong password is refused | PASS | `401 invalid_credentials`, "Incorrect email or password." | 103 |
| UAT-04 | Unauthenticated access is refused | PASS | `401 not_authenticated` | 2 |
| UAT-05 | Create a prospect manually | PASS | Lead id 1 created, stage `qualified`, e-mail normalised, website given a scheme | 17 |
| UAT-06 | Duplicate detection | PASS | Second create returned `409`; duplicate-check returned `is_duplicate: true`, `match_reason: email` | 13 |
| UAT-07 | List, search and paginate | PASS | Bare array; `X-Total-Count: 1`, `X-Page: 1`, `X-Page-Size: 5`; search found the lead | 15 |
| UAT-08 | Move between lifecycle stages | PASS | Stage `qualified` → `proposal`; derived status followed | 7 |
| UAT-09 | Import a CSV | PASS | `imported: 2`, `duplicates: 1`, `invalid: 0`, `total_rows: 3`; duplicate row 4 reported as "email already belongs to lead 1" | 13 |
| UAT-10 | Invalid input rejected | PASS | `422 validation_error` with per-field errors; nothing stored | 9 |
| UAT-11 | Company intelligence | PASS | 1 need, 1 opportunity, qualification present, `provider: heuristic`; 1 insight row persisted | 29 |
| UAT-12 | Outreach generated, edited, retrieved | PASS | Campaign 1, channel `Email`, body 218 characters; edit accepted; history returned 1 row | 40 |
| UAT-13 | Send is visibly unavailable | PASS | `501 email_transport_not_configured` with a message naming SRS D-05 | 7 |
| UAT-14 | Score explainable and honest | PASS | Score 90, priority `hot`, `conversion_probability: null`, model `heuristic:deterministic-heuristic-v1`; latest-score read-back succeeded | 36 |
| UAT-15 | Next-best-action | **PARTIAL** | Priority `High`, timing "Within one business day", follow-up draft present; **no channel field** - BUG-006 | 10 |
| UAT-16 | Conversation summarised and stored | PASS | Summary produced, 4 discussion points, 1 action item; 1 interaction stored | 26 |
| UAT-17 | CRM sync fails safely | PASS | `501 crm_not_configured` with `sync_log_id: 1`; sync log grew 0 → 1; lead still readable | 43 |
| UAT-18 | Dashboard KPIs honest | PASS | `total_leads: 3`, `conversion_rate: 0.0`, `pipeline_value: null`, `pending_definition: true` | 23 |
| UAT-19 | Follow-up panel data | PASS | 1 row, highest priority `hot` | 11 |
| UAT-20 | Role-based access control | PASS | Viewer created (id 2); viewer write `403`; viewer read `200`; viewer user-admin `403` | 244 |
| UAT-21 | Delete a prospect | PASS | `204`, then `404` on read | 20 |

---

## 2. Evidence excerpts

### UAT-05 - prospect created and normalised

```
created lead id=1 stage=qualified status=Active
```

The input website was `northwind.example`; the stored value carries an `https://` scheme.
The e-mail was supplied with mixed case and stored lower-cased.

### UAT-09 - import report

```json
{
  "filename": "uat-leads.csv",
  "imported": 2,
  "duplicates": 1,
  "invalid": 0,
  "total_rows": 3,
  "errors": [{ "row": 4, "error": "email already belongs to lead 1" }],
  "duplicate_rows": [4],
  "skipped": 1
}
```

A duplicate row does not abort the import; the two valid rows are stored and the collision
is reported with the row number and the reason.

### UAT-14 - score, with the honest probability

```
score=90 priority=hot probability=None model=heuristic:deterministic-heuristic-v1
```

`probability=None` is the intended result, not a failure. The score is explainable and the
conversion probability is withheld because no calibrated model exists.

### UAT-15 - the partial result

```
Failure: FR-032 partially met: timing and content are returned, but no explicit channel
field exists (BUG-006).
priority=High timing='Within one business day'
deviation: response has no channel/channel_hint field
```

This was the only non-passing workflow at the time of the run. It was not rounded up to a
pass.

**Post-run update (27 October 2026).** BUG-006 is fixed: the recommendation contract now
carries `suggested_channel` (`email` when outreach is justified, `null` when it is not), and
`tests/test_api_ai.py::test_recommendation_endpoint` asserts timing, channel and draft
together. The 21-workflow run above was not repeated, so its recorded verdicts are unchanged;
UAT-15's blocker is closed and re-verified at the API level. See `bug-log.md` BUG-006 and
`milestone-test-report.md` section 3.2.

### UAT-17 - a failed sync does not damage local data

```
code=crm_not_configured meta={'sync_log_id': 1}
sync log rows 0 -> 1
```

The failed attempt is auditable, and the lead remains readable afterwards.

### UAT-18 - the dashboard tells the truth

```
total_leads=3 conversion_rate=0.0 pipeline_value=None pending=True
```

`conversion_rate: 0.0` is a computed value (no lead has converted yet). `pipeline_value` is
`null` because SRS D-10 has not defined it. A dashboard that showed `0` here would be
lying about the pipeline.

### UAT-20 - role separation

```
created viewer id=2
viewer write denied with 403
viewer read allowed
viewer user administration denied
```

---

## 3. Observations for the frontend owner

These are not defects; they are facts the Streamlit implementation must respect.

1. `GET /leads` returns a **bare array**. The total is in `X-Total-Count`, not in the body.
2. `id` values are serialised as **strings**.
3. Three KPIs arrive as `{"value": null, "definition": "...", "pending_definition": true}`.
   The UI must render "not defined yet", never `0`.
4. `POST /outreach/send` and `POST /crm/sync` return `501`. Disable or clearly label the
   controls and show the returned `detail`.
5. `conversion_probability` is `null` for the current engine. Do not display a probability
   gauge; display the score and the band with its note.
6. AI output must be requested from the server. The frontend must not compute or post AI
   results itself.

---

## 4. Retest notes

* The database was rebuilt with `alembic downgrade base` then `alembic upgrade head`
  immediately before the run, so the result is not influenced by earlier data.
* The runner generates a unique e-mail per run, so re-running against the same database
  does not produce false duplicate failures.
* The run took 21 workflows; total wall-clock time was dominated by password hashing in
  UAT-02 and UAT-20 (105 ms and 244 ms), not by AI calls.

---

## 5. Sign-off

| Role | Name | Statement |
|---|---|---|
| QA / Test Engineer | Mohamed Isharak M | 20 of 21 workflows accepted; 1 partial with a linked defect; 0 failures |
| Backend owner | M Doran | Pending review of this report |
| Database owner | Marri Sai Surekha | Pending - UAT must be re-run after the schema merge |
| Frontend owner | Maheksaba Akbar Shaikh | Pending - UI workflows not yet executable |
