# Backend, canonical schema and intelligence integration

## What this PR does

Replaces the non-importable Team-C scaffold with a runnable, tested FastAPI backend and the
canonical PostgreSQL schema, and defines a typed boundary for the AI layer so Mahidhar's package
can be integrated through his own PR without copying it.

The baseline on `main` fails at import:

```
backend/api.py:10: in <module>
    from ai.providers import create_provider
E   ModuleNotFoundError: No module named 'ai'
```

## Scope

- **Backend**: app factory, 7 routers, services, Pydantic schemas, JWT auth + RBAC, CLI.
- **Database**: canonical eight tables (`users`, `leads`, `company_insights`,
  `outreach_campaigns`, `lead_scores`, `sales_interactions`, `crm_sync_logs`, `sales_analytics`)
  with indexes, cascade rules and a unique normalised `email_key`.
- **Migration**: explicit DDL revision replacing the `Base.metadata.create_all()` stub.
- **Intelligence**: `IntelligenceEngine` protocol, a deterministic offline `HeuristicEngine`
  (default), and an `ExternalAIEngine` adapter for `ai.*` that is only enabled with
  `SALES_GENIE_AI_BACKEND=external`.
- **Tests**: 122 tests, green on SQLite and PostgreSQL 16.
- **Packaging**: pinned requirements, `.env.example`, non-root `Dockerfile`, two-service Compose.
- **Docs**: audit, database/AI reviews, API contract, frontend hand-off, test report,
  contributor actions, milestone readiness.

## What this PR deliberately does not do

| Item | Behaviour |
|---|---|
| Email delivery | `POST /outreach/send` returns `501` (SRS D-05) |
| Calibrated conversion probability | `conversion_probability` is `null`; the band is labelled uncalibrated |
| Undefined KPIs | `pipeline_value`, `average_response_time_days`, `average_sales_cycle_days` are `null` with `pending_definition: true` (SRS D-10) |
| Live CRM sync | Validated, dry-run preview, failures logged, transport returns `501` (SRS D-06) |
| Follow-up status updates | List is read-only; no recommendations table exists |
| Streamlit frontend | Excluded; Maheksaba's PR |
| `ai/` and `utils/` | Excluded; Mahidhar's PR |
| CI workflow | Not added; proposal in `docs/contributor-actions.md` |

## Verification

```powershell
$env:JWT_SECRET = "<random>"
python -m pytest -q                                   # 116 passed, 6 skipped
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55432/salesgenie_test"
python -m pytest -q                                   # 122 passed
docker compose config --quiet                         # exit 0
```

Exact commands, environment versions and output: `docs/test-report.md`.

**Not verified in this environment:** Docker image build and container start (daemon unavailable),
`SALES_GENIE_AI_BACKEND=external` (package not merged), real provider calls, browser CORS.

## Review notes

- `backend/config.py` fails fast when `AUTH_ENABLED=true` and `JWT_SECRET` is unset; there is no
  default credential anywhere in the repository.
- The API owns AI calls. The frontend must not compute AI output or hold provider keys; this
  inverts the assumption in `team-c-mahi/docs/backend_api_contract.md` and is documented in
  `docs/ai-review.md` section 5.
- The four score factors map to SRS FR-030. Mahidhar's eight-factor model is accepted by the
  adapter but needs a `dimension` mapping before the UI can present four cards.
- `docs/SRS.md` is a copy of the authoritative SRS for in-repo reference; the source of truth
  remains the project documentation.

## Attribution

`team_c_sai` and `team-c-mahi` were reviewed read-only. No file from either repository was copied
into this branch; their work must land through their own pull requests. This branch was authored
by Mohamed Isharak M under his own Git identity.
