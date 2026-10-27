# Milestone Readiness Assessment

**Date:** 27 October 2026
**Assessment by:** Mohamed Isharak M
**Branch assessed:** `fix/open-defects` (on top of `main` at `46663fe`)

This assessment separates what is **demonstrably working** from what is **implemented but
unverified** and what is **not implemented**. It is intended to be read before the milestone
review so the team does not overclaim.

---

## 1. Overall readiness

| Layer | Readiness | Basis |
|---|---|---|
| Backend API | **Ready to demonstrate** | 156 automated tests pass on PostgreSQL 16.15 (150 on SQLite) |
| Database schema + migration | **Ready to demonstrate** | `alembic upgrade head` verified on both engines; parity tests |
| Authentication / RBAC | **Ready to demonstrate** | Login, expiry, forged token, role matrix tested; live with `AUTH_ENABLED=true` |
| AI intelligence (heuristic) | **Ready to demonstrate** | Deterministic, offline, tested for honesty and validation |
| AI intelligence (external package) | **Ready to demonstrate with the mock provider** | Package merged; six-operation gate passes |
| Outreach generation | **Ready to demonstrate** | Draft generation and persistence tested |
| Email sending | **Not implemented** | Returns `501` by design |
| Lead scoring | **Ready to demonstrate as heuristic** | Four factors, explainable, no fake probability |
| Conversion probability | **Not implemented** | `null` with an uncalibrated band |
| Analytics / dashboard data | **Ready to demonstrate, with null KPIs** | Undefined metrics flagged |
| CRM integration | **Not implemented** | Dry-run + failure logging only |
| Docker packaging | **Ready to demonstrate** | Built and started; db, api and frontend healthy |
| Streamlit frontend | **Ready to demonstrate; human acceptance pending** | Merged UI, 12/12 gate, AppTest and a browser check |
| CI pipeline | **Not implemented** | Proposed in contributor actions |

**Bottom line:** the project is **end-to-end ready for a local demonstration**: the frontend
is merged, the Docker stack runs, and the full suite passes on both databases. Production
hardening (TLS, secrets manager, real e-mail/CRM providers, CI) is still pending.

---

## 2. What can be demonstrated live today

All of the following run from a clean checkout with no external credentials.

1. **Install and migrate**
   ```powershell
   pip install -r requirements-dev.txt
   $env:JWT_SECRET = "<random>"
   $env:DATABASE_URL = "postgresql+psycopg://.../salesgenie"
   python -m alembic upgrade head
   ```
2. **Create an admin and start the API**
   ```powershell
   python -m backend.cli create-user --email lead@example.com --role admin
   uvicorn main:app --reload
   ```
3. **Authenticate** at `/docs` or with `POST /api/v1/auth/token`.
4. **Create, list, filter, paginate, update and delete leads.**
5. **Import a CSV** and show the row-level report (imported, duplicates, invalid, skipped).
6. **Duplicate detection** on create, update and import.
7. **Generate company intelligence** and show facts vs hypotheses and the missing-information list.
8. **Generate an outreach draft**, edit it, and show that "send" returns `501`.
9. **Score a lead**, show the four factors and the explicit "not a calibrated probability" note.
10. **Summarise a conversation**, showing extracted action items and the uncertainty list.
11. **Show analytics** with `null` for undefined KPIs and a definition string.
12. **Show RBAC**: a `viewer` cannot create; a `rep` cannot delete; only an `admin` can manage
    users.
13. **Show the OpenAPI spec** at `/openapi.json`.

Suggested demo script (10 minutes):

| Minute | Action | Point to make |
|---|---|---|
| 1 | `GET /api/v1/health` | Database and AI backend are live |
| 2 | Login, show `/auth/me` | Real JWT, real role |
| 3 | Import CSV | Validation + per-row reporting |
| 4 | Duplicate create | 409 with matched lead id |
| 5 | Generate insights | Facts separated from hypotheses |
| 6 | Generate outreach | Persisted draft; send disabled |
| 7 | Score lead | Four explainable factors; probability is null |
| 8 | Summarise conversation | Only extracted commitments |
| 9 | Analytics | Null KPIs are explicitly flagged |
| 10 | Viewer/rep attempts | 403 responses |

---

## 3. What is implemented but must be verified before claiming

| Item | Why it is not claimed yet | Verification needed |
|---|---|---|
| Real provider calls (Grok/Gemini/OpenAI) | No credentials used | A controlled test with a real key in a non-production environment |
| Long-running/load behaviour | Not tested | Optional: a small load test on `/leads` |
| Human usability of the UI | The browser check covered the scoring path, not every screen | A person completes login -> import -> intelligence -> outreach -> score -> dashboard |

---

## 4. What is not implemented (and must not be presented as done)

| Feature | Current behaviour | SRS reference |
|---|---|---|
| Email delivery | `POST /outreach/send` -> `501` | D-05 |
| Calibrated conversion probability | `conversion_probability = null`; uncalibrated band | FR-041, D-10 |
| Pipeline value, response time, sales cycle | `null` + `pending_definition = true` | FR-046..FR-053, D-10 |
| Live CRM sync | `501`; failure logged | D-06 |
| Follow-up status updates | Read-only derived list (BUG-011) | FR-052 |
| CI pipeline | No workflow file | NFR-009 |
| Trained ML model / accuracy metrics | None; heuristic only | FR-035..FR-043 |

If a reviewer asks for any of these, the correct answer is "not implemented; here is the design
decision and the next step", not a demonstration of a stand-in.

---

## 5. Traceability snapshot

| SRS area | Status | Where |
|---|---|---|
| FR-001..FR-015 lead management | Implemented, tested | `backend/routers/leads.py`, `services/leads.py`, `services/csv_import.py` |
| FR-016..FR-025 company analysis | Implemented on heuristic engine | `routers/intelligence.py`, `intelligence/heuristic.py` |
| FR-026..FR-034 outreach | Implemented except delivery | `routers/outreach.py` |
| FR-035..FR-043 scoring | Implemented as heuristic; no calibrated model | `routers/scoring.py` |
| FR-044..FR-048 conversation intelligence | Implemented | `routers/conversations.py` |
| FR-049..FR-051 CRM | Dry-run + logging only | `routers/analytics.py` |
| FR-052..FR-053 analytics | Implemented; three KPIs pending definition | `services/analytics.py` |
| NFR-005 auth/RBAC | Implemented, tested | `security.py`, `deps.py`, `routers/auth.py` |
| NFR-009 testing | Implemented, 156 tests on PostgreSQL | `tests/` |
| NFR-010 deployment | Verified: Compose stack builds and all three services are healthy | `Dockerfile`, `docker-compose.yml` |

This snapshot is intentionally conservative; the detailed requirement text remains in
[`SRS.md`](SRS.md).

---

## 6. Risks for the review

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Reviewer expects a working UI | Low | Low | Open `http://127.0.0.1:8501` from the Compose stack; state that human acceptance is pending |
| Reviewer expects AI-generated email to be sent | Medium | Medium | Show the `501` and the SRS D-05 rationale |
| Reviewer expects a trained model / accuracy | Medium | High | Show the heuristic methodology note; the UI shows the engine name, not an accuracy figure |
| Docker build fails on the review machine | Low | Medium | The stack was built and run here; rebuild before the review |
| External AI path fails after merge | Low | Medium | Run `scripts/check_ai_integration.py` before merging; it must print 6/6 |
| Undefined KPIs look like bugs | Medium | Low | The UI/documentation must say "pending definition" |

---

## 7. Definition of "milestone complete"

The milestone can be called complete when all of the following are true:

- [x] Backend branch merged to `main` after review.
- [x] `docker compose up --build` succeeds and `GET /api/v1/health` returns `status: ok`.
- [x] The external AI engine has been exercised once with the merged `ai/` package (mock provider).
- [x] The frontend is merged and the scoring path was completed in a browser; a full human
      acceptance pass over every screen is still pending.
- [ ] CI runs the test suite on every PR.
- [x] The documentation in `docs/` reflects the merged state.

The accurate statement today is: **backend, database, AI integration, frontend and the Docker
stack are complete and verified for a local demonstration; CI and production hardening are
pending.**
