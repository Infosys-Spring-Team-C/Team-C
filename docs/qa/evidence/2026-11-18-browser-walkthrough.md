# Browser walkthrough - Conversations page (18 November 2026)

**Purpose:** close the visual-acceptance gap recorded on 17 November 2026, when the
walkthrough was blocked by host memory (`OpenBLAS` allocation error,
`ERR_INSUFFICIENT_RESOURCES`).

**Result: PASS for functional browser presentation.** The page was opened in the in-app
Chromium browser against a running API and Streamlit server, with real stored data. Pixel-level
styling was not captured because the browser tool reported that the desktop window was not
visible for a screenshot; the evidence below is the rendered DOM text, layout metrics and
console state.

## Environment

| Item | Value |
|---|---|
| Date | 18 November 2026 |
| API | `http://127.0.0.1:8000` (uvicorn, `main:app`) |
| Database | SQLite, isolated file `browser_m3.db` |
| AI backend | `heuristic` (deterministic) |
| Auth | enabled; `qa.admin@example.com` (admin) |
| UI | `http://127.0.0.1:8501` (Streamlit, headless server) |
| Browser | in-app Chromium, viewport 822 x 654 |

## Steps executed

1. Created an admin user and initialised the schema (`backend.cli init-db`,
   `backend.cli create-user`).
2. Started the API on port 8000 and Streamlit on port 8501 with
   `SALES_GENIE_BACKEND_BASE_URL=http://127.0.0.1:8000` and a backend token for the admin.
3. Created prospect `Northwind Traders` / `Priya Raman` through `POST /api/v1/leads`.
4. Stored a call summary through `POST /api/v1/conversations/summarize`.
5. Ran three simulated CRM syncs (`sync_contact`, `activity_log`, `update_stage`) through
   `POST /api/v1/crm/sync` with `"simulate": true`.
6. Opened the Conversations page in the browser and read the rendered output.

## Observed

Page title: `SalesGenie AI - Sales Intelligence`.

| Section | Present | Evidence in the rendered page |
|---|---|---|
| Prospect selector | yes | `Priya Raman · Logistics` in the active-prospect panel |
| New summary / transcript | yes | `The backend extracts only what the transcript contains` |
| Latest summary | yes | summary text including `pricing proposal by Friday` |
| CRM sync status | yes | `CONNECTIVITY Simulated`, `SYNCS (24H) 3`, `FAILURES (24H) 0`, `0.0% failure rate` |
| Providers | yes | `Salesforce: not_configured · Hubspot: not_configured` |
| Simulated-transport label | yes | `Simulated transport: no Salesforce or HubSpot request is made (SRS D-06)` |
| Run a sync | yes | provider and workflow controls, `Run simulated sync` |
| Field mapping | yes | `Canonical field → CRM field`, operations listed |
| Recent activity | yes | three CRM rows (`contact`, `activity`, `deal`, all `success`) and the call summary |
| History | yes | `18 Nov 2026, 07:19 · Call` |

Layout and console checks:

| Check | Result |
|---|---|
| Horizontal overflow | none (`scrollWidth 822` = `clientWidth 822`) |
| Console errors | 0 |
| Authentication state | `QA Admin · admin · qa.admin@example.com` |
| Backend state | `Backend connected` / `Backend online` |

The page states that the CRM transport is simulated and does not claim a live Salesforce or
HubSpot call.

## What this does and does not prove

* **Proves:** the Conversations page renders in a real browser, receives live API data, lists
  stored summaries and CRM sync rows, exposes the sync controls and the field map, and does not
  overflow its viewport or log a console error.
* **Does not prove:** pixel-level visual quality (spacing, colour, typography) or behaviour at
  other viewport sizes. No screenshot was captured; the desktop window was not visible to the
  screenshot tool.

## Verdict

`FR-044` and `AC-023` move from `PARTIAL` to `PASS` on the strength of this functional browser
walkthrough. The visual-styling caveat is recorded rather than hidden.
