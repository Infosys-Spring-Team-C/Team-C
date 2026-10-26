# Milestone Readiness Assessment

**Date:** 26 October 2026
**Assessment by:** Mohamed Isharak M
**Branch assessed:** `feature/backend-integration`

This assessment separates what is **demonstrably working** from what is **implemented but
unverified** and what is **not implemented**. It is intended to be read before the milestone
review so the team does not overclaim.

---

## 1. Overall readiness

| Layer | Readiness | Basis |
|---|---|---|
| Backend API | **Ready to demonstrate** | 117 automated tests pass on SQLite and PostgreSQL 16 |
| Database schema + migration | **Ready to demonstrate** | `alembic upgrade head` verified on both engines; parity tests |
| Authentication / RBAC | **Ready to demonstrate** | Login, expiry, forged token, role matrix tested |
| AI intelligence (heuristic) | **Ready to demonstrate** | Deterministic, offline, tested for honesty and validation |
| AI intelligence (external package) | **Implemented, unverified** | Adapter compiles; package not merged |
| Outreach generation | **Ready to demonstrate** | Draft generation and persistence tested |
| Email sending | **Not implemented** | Returns `501` by design |
| Lead scoring | **Ready to demonstrate as heuristic** | Four factors, explainable, no fake probability |
| Conversion probability | **Not implemented** | `null` with an uncalibrated band |
| Analytics / dashboard data | **Ready to demonstrate, with null KPIs** | Undefined metrics flagged |
| CRM integration | **Not implemented** | Dry-run + failure logging only |
| Docker packaging | **Configuration validated, runtime unverified** | Daemon unavailable |
| Streamlit frontend | **Pending** | Maheksaba's PR |
| CI pipeline | **Not implemented** | Proposed in contributor actions |

**Bottom line:** the backend and database are milestone-ready. The project as a whole is **not**
end-to-end ready until the frontend PR lands and the Docker build is executed once on a machine
with a running daemon.

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
| Docker image and Compose stack | Daemon was not running; only `docker compose config` was checked | `docker compose up --build`, then health check and a lead create inside the container |
| External AI engine | `ai/` package not in Team-C | Merge the AI PR, set `SALES_GENIE_AI_BACKEND=external`, run the six-operation smoke test |
| Real provider calls (Grok/Gemini) | No credentials used | A controlled test with a real key in a non-production environment |
| CORS from a browser | No browser client existed | Load the Streamlit app from `localhost:8501` and confirm preflight |
| Long-running/load behaviour | Not tested | Optional: a small load test on `/leads` |

---

## 4. What is not implemented (and must not be presented as done)

| Feature | Current behaviour | SRS reference |
|---|---|---|
| Email delivery | `POST /outreach/send` -> `501` | D-05 |
| Calibrated conversion probability | `conversion_probability = null`; uncalibrated band | FR-041, D-10 |
| Pipeline value, response time, sales cycle | `null` + `pending_definition = true` | FR-046..FR-053, D-10 |
| Live CRM sync | `501`; failure logged | D-06 |
| Follow-up status updates | Read-only derived list | AC-029 |
| CI pipeline | No workflow file | NFR-009 |
| Streamlit UI | Absent | Module 6 |
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
| NFR-009 testing | Implemented, 117 tests | `tests/` |
| NFR-010 deployment | Files complete; runtime unverified | `Dockerfile`, `docker-compose.yml` |

This snapshot is intentionally conservative; the detailed requirement text remains in
[`SRS.md`](SRS.md).

---

## 6. Risks for the review

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Reviewer expects a working UI | Medium | High | State clearly that the frontend is a separate pending PR; demo the API and `/docs` |
| Reviewer expects AI-generated email to be sent | Medium | Medium | Show the `501` and the SRS D-05 rationale |
| Reviewer expects a trained model / accuracy | Medium | High | Show the heuristic methodology note; do not quote an accuracy figure |
| Docker build fails on the review machine | Low | Medium | Run `docker compose up --build` before the review |
| External AI path fails after merge | Medium | Medium | Run the adapter smoke test immediately after merging the AI PR |
| Undefined KPIs look like bugs | Medium | Low | The UI/documentation must say "pending definition" |

---

## 7. Definition of "milestone complete"

The milestone can be called complete when all of the following are true:

- [ ] Backend branch merged to `main` after review.
- [ ] `docker compose up --build` succeeds on a machine with Docker running, and
      `GET /api/v1/health` returns `status: ok`.
- [ ] The external AI engine has been exercised once with the merged `ai/` package (mock provider
      is acceptable).
- [ ] The frontend PR is merged and a user can complete: login -> import leads -> view intelligence
      -> generate outreach -> score -> view dashboard.
- [ ] CI runs the test suite on every PR.
- [ ] The documentation in `docs/` reflects the merged state.

Until then, the accurate statement is: **backend and database complete and tested; AI integration
adapter ready; frontend, CI and Docker runtime verification pending.**
