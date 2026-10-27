# SalesGenie AI - Streamlit frontend

This is the presentation layer contributed by **Maheksaba Akbar Shaikh**
(`Mahek-saba/frontend-infosys`, branch `frontend-ui`, commit `9972f8d`).
The screens, styling and copy are hers. Only the API boundary was adapted so
the UI talks to Team-C's canonical backend instead of a second backend.

```
frontend/
|-- app.py              # the UI (Mahek's, with three minimal integration patches)
|-- api_compat.py       # translates the UI's calls onto /api/v1 (lead's work)
|-- requirements.txt    # pinned client dependencies
`-- .streamlit/
    `-- config.toml     # theme and headless server settings
```

The frontend holds **no database credentials and no LLM provider keys**. All AI
work happens in the backend; the UI only sends HTTP requests.

---

## 1. Run it

Start the API first (see the root `README.md`), then:

```powershell
python -m pip install -r frontend/requirements.txt

$env:SALES_GENIE_BACKEND_BASE_URL = "http://127.0.0.1:8000"
# If the API has AUTH_ENABLED=true, supply credentials or a token:
# $env:SALES_GENIE_BACKEND_TOKEN = "<bearer token>"
# or
# $env:SALES_GENIE_BACKEND_EMAIL = "you@example.com"
# $env:SALES_GENIE_BACKEND_PASSWORD = "<password>"

python -m streamlit run frontend/app.py
```

The UI opens at `http://localhost:8501`. It also reads Streamlit's `BACKEND_URL`
secret if you prefer `.streamlit/secrets.toml`, but the environment variables
above take precedence in practice and are what the checks use.

## 2. Environment variables

| Variable | Purpose |
|---|---|
| `SALES_GENIE_BACKEND_BASE_URL` | API root, e.g. `http://127.0.0.1:8000`. Defaults to `http://127.0.0.1:8000`. |
| `BACKEND_URL` | Legacy name, still accepted as a fallback. |
| `SALES_GENIE_BACKEND_TOKEN` | Bearer token. Used as-is if present. |
| `SALES_GENIE_BACKEND_EMAIL` / `SALES_GENIE_BACKEND_PASSWORD` | Used once to obtain a token when no token is supplied. |

Never put `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `DATABASE_URL` or `JWT_SECRET`
here. The frontend does not need them and must not have them.

## 3. What the adapter does

`api_compat.py` maps the paths and payloads the UI was written against onto the
canonical API, and flattens the responses back into the shapes the screens
render:

| UI call | Canonical endpoint |
|---|---|
| `GET /leads/` | `GET /api/v1/leads` |
| `POST /leads/` | `POST /api/v1/leads` |
| `POST /leads/bulk` | `POST /api/v1/leads/import` (records converted to CSV) |
| `POST /intelligence/analyze/{id}` | `POST /api/v1/leads/{id}/insights` |
| `GET /intelligence/analyze/{id}` | `GET /api/v1/leads/{id}/insights` |
| `POST /intelligence/score/{id}` | `POST /api/v1/leads/{id}/scores` |
| `GET /intelligence/score/{id}` | `GET /api/v1/leads/{id}/scores/latest` |
| `POST /intelligence/outreach` | `POST /api/v1/outreach/generate` |
| `GET /intelligence/outreach/{id}` | `GET /api/v1/leads/{id}/outreach-drafts` (latest) |
| `POST /outreach/send-email` | `POST /api/v1/outreach/send` (always `501`, by design) |
| `GET /analytics/dashboard` | `GET /api/v1/analytics` + lead industries |
| `GET /health` | `GET /health` |

A missing value stays missing. In particular `conversion_probability` is
`null`, and the UI renders **n/a - No calibrated model configured** instead of
inventing a percentage (SRS D-10/D-13).

## 4. Verification

```powershell
# Unit tests for the adapter (no server needed)
python -m pytest -q tests/test_frontend_compat.py

# Live end-to-end gate against a running API
$env:SALES_GENIE_BACKEND_BASE_URL = "http://127.0.0.1:8010"
python scripts/check_frontend_integration.py
```

Last recorded result: **17 unit tests passed**, **12/12 live checks passed**, and
the Streamlit script itself ran headlessly with **0 exceptions / 0 errors**
(`docs/qa/evidence/2026-10-27-frontend-integration-gate.txt` and
`docs/qa/evidence/2026-10-27-frontend-apptest.txt`). The UI was not clicked
through by hand in a browser; the gate calls the exact functions the screens
call, and AppTest executes the same top-level script a browser session runs.

## 5. Known limits

* E-mail sending is intentionally unavailable (`501`); the UI surfaces the
  backend's message instead of pretending a message was sent.
* The UI's "funding stage" and "pipeline stage" lists are her original labels;
  the adapter maps them onto the canonical lifecycle stages and ignores a label
  it cannot map rather than guessing.
* `docker compose` starts the API and database only. The frontend service is
  defined but the image was never built here (no Docker daemon), so that path is
  unverified - see BUG-012 in `docs/qa/bug-log.md`.
