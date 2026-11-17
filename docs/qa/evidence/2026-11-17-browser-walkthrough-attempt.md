# Browser walkthrough attempt - Conversations page (blocked)

**Date:** 2026-11-17, 20:05-20:16 UTC
**Operator:** Mohamed Isharak M
**Purpose:** click through the new Conversations sections (CRM status, field map, sync
form, activity feed, history) in the in-app browser, to move FR-044 / AC-023 from
`PARTIAL` to `PASS`.
**Outcome:** **BLOCKED** - the host could not keep Streamlit alive. No walkthrough was
performed and no visual acceptance is claimed.

## Environment

| Item | Value |
|---|---|
| Host RAM | 16 GB total, 3.1 GB free at the start of the attempt |
| API | uvicorn on `http://127.0.0.1:8011`, SQLite, heuristic engine - healthy |
| Frontend | `python -m streamlit run frontend/app.py --server.port 8501 --server.headless true` |
| Browser | in-app Chromium tab on `http://127.0.0.1:8501` |
| Docker | not used (daemon unavailable) |

## Attempts

| # | Time | Setup | Observed | Result |
|---|---|---|---|---|
| 1 | 20:05 | Default Streamlit start | Page shell loaded, then Chromium failed every static chunk with `net::ERR_INSUFFICIENT_RESOURCES`. Streamlit stderr: `OpenBLAS error: Memory allocation still failed after 10 retries, giving up.` The process exited and port 8501 closed. | Failed |
| 2 | 20:09 | `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` | The app rendered its sidebar and navigation (Conversations button visible), but the server died during the first data render. The browser then received `502 Bad Gateway`; the health endpoint stopped answering. No traceback was written. | Failed |
| 3 | 20:15 | Same limits, fresh process | `/_stcore/health` answered `200` once, then the browser received `502 Bad Gateway` and the process was gone. | Failed |

## What was verified despite the failure

The rendered shell in attempt 2 showed the navigation and the page title, and the API
behind the page was healthy throughout (25/25 live UAT, plus the headless render check).
What could not be observed is the visual result of the new Conversations sections.

## Consequence

* FR-044 and AC-023 stay **PARTIAL**. They are not marked `PASS` on the strength of an
  API contract or a headless render alone.
* The headless Streamlit render check (`2026-11-17-conversations-headless-render.txt`)
  is recorded as stronger partial evidence, not as a substitute for the walkthrough.
* The walkthrough should be repeated on a host with more free memory, or inside the
  Compose stack once Docker is available.

## Housekeeping

The local, git-ignored `.streamlit/secrets.toml` was pointed at `http://127.0.0.1:8011`
for the attempt and restored to its original `http://127.0.0.1:8000` value afterwards.
No application file was modified for this attempt.
