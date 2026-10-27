# Frontend Integration Guide (for Maheksaba)

This document is the hand-off for the Streamlit frontend. The backend is runnable and testable on
its own; the frontend is expected to arrive through its own pull request.

> **Status, 27 October 2026 - integrated and running.** Maheksaba's `frontend-ui` branch has
> been merged and `frontend/api_compat.py` translates her UI's calls onto the canonical
> `/api/v1` contract. The adapter passes 12/12 live checks, `AppTest` runs with 0 exceptions,
> and the Docker Compose stack (PostgreSQL + API + Streamlit) was built and verified with all
> three services healthy. The checklist in section 10 describes the canonical contract; the
> actual implementation status, the four UI patches and the open items are in
> [`docs/frontend-merge-notes.md`](frontend-merge-notes.md). Where this guide and the merged
> adapter differ, the adapter is authoritative and the differences are recorded in the merge
> notes.

**Do not copy Mahidhar's temporary Streamlit app.** It is a demo with in-memory state and is not
the final UI.

---

## 1. Start the backend

```powershell
# Terminal 1 - PostgreSQL (or use SQLite for a quick start)
docker compose up -d db

# Terminal 2 - API
$env:DATABASE_URL = "postgresql+psycopg://salesgenie:...@localhost:5432/salesgenie"
$env:JWT_SECRET = "<long random value>"
python -m alembic upgrade head
python -m backend.cli create-user --email you@example.com --role admin
uvicorn main:app --reload
```

The API is at `http://127.0.0.1:8000`, docs at `/docs`, health at `/api/v1/health`.

For a SQLite-only demo, set `DATABASE_URL=sqlite:///./salesgenie.db` and skip the `db` container.

---

## 2. Frontend environment

```env
SALES_GENIE_BACKEND_BASE_URL=http://127.0.0.1:8000
SALES_GENIE_BACKEND_API_PREFIX=/api/v1
# Never put an LLM provider key in the frontend. The backend owns AI calls.
```

CORS is already configured for `http://localhost:8501` and `http://127.0.0.1:8501`. If Streamlit
runs elsewhere, add the origin to `CORS_ORIGINS` on the backend (comma-separated).

---

## 3. Authentication

The backend uses OAuth2 password flow. Store the token in `st.session_state`, never in a file.

```python
import requests
import streamlit as st

BASE = "http://127.0.0.1:8000/api/v1"

def login(email: str, password: str) -> bool:
    response = requests.post(
        f"{BASE}/auth/token",
        data={"username": email, "password": password},
        timeout=10,
    )
    if response.status_code != 200:
        st.error(response.json().get("detail", "Login failed."))
        return False
    st.session_state["token"] = response.json()["access_token"]
    return True

def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state['token']}"}
```

Handle `401` by clearing the token and returning the user to the login screen. Handle `403` with a
clear "your role cannot perform this action" message.

---

## 4. Page-to-endpoint mapping

| UI page | Endpoints | Notes |
|---|---|---|
| Login | `POST /auth/token`, `GET /auth/me` | Show role from `/auth/me` |
| Dashboard | `GET /analytics`, `GET /follow-ups` | `null` metrics mean "not defined", not zero |
| Lead Management | `GET/POST /leads`, `GET/PATCH/DELETE /leads/{id}`, `POST /leads/import`, `POST /leads/duplicate-check` | Use headers for pagination |
| Lead Intelligence | `POST/GET /leads/{id}/insights` | Call POST with no body; do not send AI output |
| Outreach Generator | `POST /outreach/generate`, `GET/POST /leads/{id}/outreach-drafts`, `PATCH /outreach/campaigns/{id}`, `POST .../mark-sent` | `POST /outreach/send` always returns 501 |
| Lead Scoring | `POST/GET /leads/{id}/scores`, `GET /leads/{id}/scores/latest` | `conversion_probability` may be null |
| Conversation Intelligence | `POST /conversations/summarize`, `GET/POST /leads/{id}/conversations` | Show `missing_or_uncertain` |
| Follow-up | `GET /follow-ups`, `GET /recommendations/{lead_id}` | Read-only for now |
| AI Configuration | `GET /health` | Report `ai_backend`, `ai_status`, `auth_enabled` |

---

## 5. Examples

### List leads with pagination

```python
response = requests.get(
    f"{BASE}/leads",
    headers=headers(),
    params={"page": 1, "page_size": 50, "query": "", "stage": "", "industry": ""},
    timeout=10,
)
response.raise_for_status()
leads = response.json()                      # bare JSON array
total = int(response.headers["X-Total-Count"])
```

Build the pager from `X-Total-Count` and `X-Page-Size`. Do not expect a `{data: [...]}` envelope.

### Create a lead

```python
payload = {
    "company_name": "Acme Systems",
    "industry": "Software",
    "contact_name": "Dana Scully",
    "email": "dana@acme.test",
    "company_size": "51-200",
    "company_description": "A growing B2B software company.",
    "prospect_role": "VP Sales",
    "explicit_needs": "Reduce manual reporting.",
    "engagement_history": "Meeting booked",
    "stage": "qualified",
}
response = requests.post(f"{BASE}/leads", headers=headers(), json=payload, timeout=10)
```

A `409` body contains `meta.matched_lead_id`; offer to open the existing lead instead of retrying.

### CSV import

```python
files = {"file": ("leads.csv", csv_bytes, "text/csv")}
response = requests.post(f"{BASE}/leads/import", headers=headers(), files=files, timeout=30)
report = response.json()
st.success(f"Imported {report['imported']} of {report['total_rows']} rows.")
st.dataframe(report["errors"])   # each entry has row + error
```

Use the same column names as the backend aliases, or download a template from the UI. Show
`duplicates`, `invalid` and `skipped` separately.

### Generate intelligence

```python
response = requests.post(
    f"{BASE}/leads/{lead_id}/insights",
    headers=headers(),
    json={"product_service": "SalesGenie AI"},
    timeout=30,
)
intel = response.json()
st.write(intel["company_overview"])
st.write(intel["qualification"]["category"])
st.write(intel["missing_information"])
```

Render `supported_facts` differently from `possible_needs` / `potential_challenges` /
`opportunities`: the latter are hypotheses. Show the `disclaimer`.

### Generate outreach

```python
payload = {
    "lead_id": lead_id,
    "tone": "professional",
    "length": "medium",
    "outreach_type": "cold_email",
    "goal": "book a discovery call",
    "pain_points": ["manual reporting"],
    "product_service": "SalesGenie AI",
    "call_to_action": "Would a short call help?",
}
draft = requests.post(f"{BASE}/outreach/generate", headers=headers(), json=payload, timeout=30).json()
st.text_input("Subject", value=draft["subject_line"] or "")
st.text_area("Body", value=draft["body"])
```

The draft is already persisted. Editing it should `PATCH /outreach/campaigns/{id}`. "Mark sent"
calls the `mark-sent` endpoint; it records the action and does not send e-mail.

### Score a lead

```python
score = requests.post(f"{BASE}/leads/{lead_id}/scores", headers=headers(), timeout=30).json()
st.metric("Score", f"{score['score']}/100")
for factor in score["factors"]:
    st.progress(factor["normalized_value"], text=f"{factor['name']} ({factor['points']}/{factor['weight']})")
if score["conversion_probability"] is None:
    st.caption(score["probability_note"])
```

Never render `probability_band` as a percentage or as "conversion probability".

### Follow-ups

```python
items = requests.get(f"{BASE}/follow-ups", headers=headers(), timeout=10).json()
```

`PATCH /follow-ups/{id}` is not available yet. Use the per-lead recommendation endpoint for the
detail panel and keep the list read-only until a recommendations table is agreed.

---

## 6. Error handling

```python
def call(method, path, **kwargs):
    response = requests.request(method, f"{BASE}{path}", headers=headers(), timeout=30, **kwargs)
    if response.status_code == 401:
        st.session_state.pop("token", None)
        st.warning("Session expired. Please sign in again.")
        st.stop()
    if response.status_code == 403:
        st.error("Your role does not allow this action.")
        return None
    if response.status_code == 422:
        st.error(response.json().get("detail", "Please check the form."))
        st.json(response.json().get("errors", []))
        return None
    if response.status_code >= 500:
        st.error(response.json().get("detail", "The server could not complete the request."))
        return None
    response.raise_for_status()
    return response
```

Always read `detail` and `code`; do not parse tracebacks or assume a `message` key.

---

## 7. Display rules (important for honesty)

1. **Null means not defined.** `pipeline_value`, `average_response_time_days` and
   `average_sales_cycle_days` are `null` with `pending_definition: true`. Render "Not defined
   (pending SRS decision)" - never `0`.
2. **Scores are heuristic.** Show `methodology_note` near any score. Do not call it "AI
   probability" or "confidence".
3. **Hypotheses are not facts.** Style `supported_facts` differently from `possible_needs`,
   `potential_challenges` and `opportunities`.
4. **Conversation summaries are transcript-only.** Show `source_note` and
   `missing_or_uncertain`.
5. **Demo data must be labelled.** If you add sample data for a demo, label it in the UI and do not
   seed it into a shared database silently.
6. **No e-mail sending.** Do not imply the app sent anything. `mark-sent` is a manual record.

---

## 8. Stage and status mapping

The API returns canonical lowercase stages:

```
prospecting, discovery, qualified, proposal, negotiation, converted, lost
```

For display you may map:

| Canonical | Suggested label |
|---|---|
| `prospecting` | Prospecting |
| `discovery` | Discovery |
| `qualified` | Qualified |
| `proposal` | Proposal |
| `negotiation` | Negotiation |
| `converted` | Closed Won |
| `lost` | Closed Lost |

`status` in responses is already derived (`New`, `Active`, `Closed`) and is read-only.

Input accepts both canonical values and aliases (`Closed Won`, `Won`, `New`, `Contacted`, ...).

---

## 9. Known gaps you must not work around silently

| Gap | What to do |
|---|---|
| `GET /leads` has no `status` filter (only `stage`, `industry`, `query`) | Filter by `stage`, or request the filter in an issue |
| `PATCH /follow-ups/{id}` is missing | Keep the follow-up list read-only |
| `POST /outreach/send` returns 501 | Show a clear "sending is not enabled in this build" message |
| `conversion_probability` is null | Show the band + note, never a fake percentage |
| CRM sync returns 501 | Show the failure and the sync-log entry; do not retry automatically |
| No refresh endpoint for insights/scores | Call the POST endpoint again to create a new version |

If a screen needs a contract change, raise it before implementing a client-side workaround.

---

## 10. Frontend checklist

- [ ] Login screen calls `/auth/token`; token kept in session state only.
- [ ] `Authorization` header attached to every request except health/token.
- [ ] 401 clears the session; 403 shows a role message.
- [ ] Lead list uses `X-Total-Count` / `X-Page-Size` for pagination.
- [ ] Create/edit forms send only documented fields.
- [ ] CSV import shows imported/duplicates/invalid/skipped and per-row errors.
- [ ] Duplicate 409 offers the existing lead.
- [ ] Intelligence page distinguishes facts from hypotheses and shows the disclaimer.
- [ ] Outreach page edits the persisted draft; no client-side AI call; no API keys.
- [ ] Scoring page shows the four factors and the heuristic note.
- [ ] Conversation page shows `missing_or_uncertain`.
- [ ] Dashboard renders `null` KPIs as "not defined".
- [ ] Follow-up page is read-only until the PATCH endpoint exists.
- [ ] No demo data written to a shared database without a visible label.
- [ ] Frontend has no database credentials and no LLM keys.
