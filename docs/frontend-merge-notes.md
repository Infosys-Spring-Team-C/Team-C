# Frontend merge notes - Maheksaba Akbar Shaikh

**Contributor:** Maheksaba Akbar Shaikh
(`Mahek-saba`, `shaikh.akbar86691@gmail.com`)
**Source:** `https://github.com/Mahek-saba/frontend-infosys`, branch `frontend-ui`,
commit `9972f8d` ("Complete frontend updates"), on top of `c08cd61`
**Merged into:** `Infosys-Spring-Team-C/Team-C`
**Date:** 27 October 2026
**Applied by:** Mohamed Isharak M (lead)

---

## 1. What was taken from her repository

Only the presentation layer:

| File | Status |
|---|---|
| `app.py` | Imported, committed under her authorship. Three minimal lead patches, listed below. |
| `.streamlit/config.toml` | Imported byte-for-byte. |
| `requirements.txt` | Replaced by a pinned three-line client list (see section 4). |

Everything was copied from her Git objects (`git show mahek/frontend-ui:<path>`)
and hash-verified against her blobs, so the UI is not a re-typed copy.

## 2. What was deliberately **not** taken

Her repository also contains a second, parallel backend:

* `main.py`, `database/connection.py`, `database/models.py`, `modules/module1..6`.
* `salesgenie.db` (a committed SQLite database), `.env.example`,
  `run_all.py`, `.vscode/`, and two PDF training guides.

Team-C already has a canonical FastAPI backend, schema and migrations. Merging a
second backend would recreate the "two implementations" problem that the
database merge had to undo. Her `modules/*` are thin wrappers around that second
backend, and her `database/` defines its own schema. They are not needed to run
her UI, which only uses `requests` against an HTTP API.

The committed `salesgenie.db` and `.env.example` were also excluded because a
repository must not carry databases or environment templates from a second
stack (and the `.env.example` contained a placeholder API key path that would
confuse this project's secret policy).

## 3. The three lead patches to `app.py`

Her screens are unchanged. The patches are the minimum needed to point the UI at
the canonical API and to stop it inventing a conversion percentage.

1. **Import and base URL.** `resolve_backend_url()` now calls
   `api_compat.resolve_base_url()`, which reads `SALES_GENIE_BACKEND_BASE_URL`
   (falling back to `BACKEND_URL`). Her Streamlit `BACKEND_URL` secret path is
   retained.
2. **Transport.** `api_get` / `api_post` delegate to
   `frontend/api_compat.py` instead of issuing raw requests to her own paths.
3. **Conversion probability.** The score card used
   `curr_score.get("conversion_probability", 0.0)` and rendered `0%` when the
   value was missing. It now renders **n/a** with the note
   *"No calibrated model configured"* when the value is `None`. This matters:
   SRS D-10/D-13 leave the model undefined, so a `0%` would have been a
   fabricated probability.

All other differences are whitespace only. A diff of her `app.py` against the
merged file should show exactly these three areas.

## 4. Dependencies

`frontend/requirements.txt` is not her original list. Her file also pinned the
backend stack (FastAPI, SQLAlchemy, uvicorn, pydantic, python-multipart,
openai). The frontend needs only:

```
streamlit==1.65.0
requests==2.34.2
pandas==2.3.3
```

Pinning is required by the project's dependency policy, and dropping the
backend packages keeps the frontend image from installing an AI SDK it must
never call directly.

## 5. Integration design

Her UI calls `/leads/`, `/intelligence/analyze/{id}`, `/outreach/send-email`
and similar paths from her own backend. Team-C's canonical paths are
`/api/v1/leads`, `/api/v1/leads/{id}/insights`, `/api/v1/outreach/send`, and
the response shapes are nested rather than flat.

Two options were considered:

* add legacy alias routes to the backend, or
* translate in the frontend.

The translation layer was chosen (`frontend/api_compat.py`). It keeps the
canonical API free of UI-specific aliases and puts every shape difference in one
tested file. The full endpoint map is in `frontend/README.md` and
`docs/frontend-integration.md`.

## 6. Authorship and history

* Commit `3cc616d` is authored by **Mahek Shaikh
  `<shaikh.akbar86691@gmail.com>`** and committed by the lead, with
  `Authored-by` / `Applied-by` trailers in the message.
* Her upstream history (`c08cd61`, `9972f8d`) was fetched, not rewritten. No
  force-push and no squash was used.
* The adapter, tests, gate script and documentation are the lead's own work
  under `isharak7m`.
* Nothing in her repository was modified; it remains read-only.

## 7. Verification

| Check | Result |
|---|---|
| `tests/test_frontend_compat.py` | **17 passed** (adapter translation only, no server) |
| `scripts/check_frontend_integration.py` against a live API | **12/12 checks passed** |
| `frontend/app.py` executed headlessly with Streamlit `AppTest` | **0 exceptions, 0 errors**; all 8 action buttons and 11 selects rendered |
| Full backend suite after the merge | see `docs/qa/milestone-test-report.md` |
| Browser click-through | **not performed**; the gate calls the same functions the screens call |

Evidence: `docs/qa/evidence/2026-10-27-frontend-integration-gate.txt` and
`docs/qa/evidence/2026-10-27-frontend-apptest.txt`.

The live run used SQLite, `AUTH_ENABLED=false`, and the external AI engine with
its **mock** provider. It proves the request/response translation; it does not
prove real-model output or the Docker frontend image (BUG-012).

A defect found during this verification is worth recording: the first version of
the adapter treated `GET /leads/{id}/insights` as a single object, but the
canonical endpoint returns a **list** of saved analyses (newest first), and the
analysis payload is flat rather than nested. The adapter now handles both the
flat POST shape and the persisted GET shape, and the live check was tightened so
a default placeholder text can no longer count as a pass.

## 8. Open items

* The frontend service in `docker-compose.yml` is defined but its image was
  never built here (no Docker daemon).
* Authentication was exercised only with `AUTH_ENABLED=false`; the token and
  email/password paths are implemented and unit-tested but not run against a
  live auth-enabled server.
* Her UI was not visually reviewed in a browser during this merge; only its
  imports and the adapter contract were executed.
* `.streamlit/config.toml` disables CORS and XSRF protection
  (`enableCORS = false`, `enableXsrfProtection = false`). That is acceptable for
  a local demo behind a loopback port, but it must be revisited before any
  shared deployment. It was left unchanged to keep her file byte-identical;
  changing it is a deployment decision, not an integration fix.
* Streamlit 1.65 warns that `use_container_width` is deprecated after
  2025-12-31. The pinned version still supports it, so the UI runs now, but a
  future Streamlit upgrade will require replacing those arguments in `app.py`.
  This is a maintenance item for the frontend owner, not a defect in this merge.
