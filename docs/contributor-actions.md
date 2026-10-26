# Contributor Action List

This file lists what each contributor should change **in their own workspace** before opening a
pull request to Team-C. It exists so contributions remain attributable and reviewable.

No work in this repository should be copied into an individual's repository, and no individual's
code should be copied into Team-C to bypass a PR.

---

## 1. Marri Sai Surekha - database / DevOps

**Repository:** `team_c_sai`
**Review:** [`database-review.md`](database-review.md)
**Target:** one PR to `Infosys-Spring-Team-C/Team-C`

### Must fix before the PR

- [ ] **Remove every default credential.** `alembic.ini`, `src/database/connection.py` and
      `docker-compose.yml` currently fall back to `postgres_password`. Require `DATABASE_URL` and
      `${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}`.
- [ ] **Do not merge the reduced schema.** The current `leads`, `company_insights`,
      `outreach_campaigns`, `lead_scores`, `sales_interactions` and `crm_sync_logs` tables cannot
      store Modules 2-4 output. Rebase on
      `alembic/versions/0001_canonical_schema.py` and add changes as a **new** revision.
- [ ] **Choose one source of DDL.** Delete `init_schema.sql` (or replace it with a bootstrap that
      runs Alembic). Two sources will drift.
- [ ] **Make `sales_analytics` team-scoped.** `user_id NOT NULL` blocks team metrics; make it
      nullable or add a scope column.
- [ ] **Preserve CRM audit history.** Change `crm_sync_logs.lead_id` to `NULL` +
      `ON DELETE SET NULL`.
- [ ] **Align column lengths with the API** (`company_name` 240, `email` 320, `website` 500).
- [ ] **Add a schema-parity test** that runs `alembic upgrade head` and compares `inspect(engine)`
      with `Base.metadata`.
- [ ] **Add CI** with a `postgres:16` service, `alembic upgrade head`, `pytest`, and the parity
      test. A workflow sketch is below.

### Recommended

- [ ] Add an API service to Compose with `depends_on: condition: service_healthy`.
- [ ] Bind PostgreSQL to `127.0.0.1` in Compose.
- [ ] Remove `container_name` so the stack can scale.
- [ ] Pin `requirements.txt`.
- [ ] Add a backup/restore/retention runbook (SRS section 13).

### Suggested CI workflow (adapt, do not paste blindly)

```yaml
name: backend-ci
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: salesgenie_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      JWT_SECRET: ci-only-secret-value-0123456789
      TEST_DATABASE_URL: postgresql+psycopg://postgres:postgres@localhost:5432/salesgenie_test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: python -m alembic upgrade head
      - run: python -m pytest -q
```

### Do not include

- `.env`, real passwords, tokens or API keys.
- A second Alembic head that conflicts with `0001_canonical_schema`.
- Kubernetes or extra infrastructure; it is out of scope.

---

## 2. Mahidhar Reddy - AI / ML

**Repository:** `team-c-mahi`
**Review:** [`ai-review.md`](ai-review.md)
**Target:** one PR to `Infosys-Spring-Team-C/Team-C`

### Must do before the PR

- [ ] **Contribute only the AI package.** Add `ai/` and the non-Streamlit parts of `utils/`.
      Do **not** add `app.py`, `pages/`, `components/`, `services/api_client.py` or
      `integrations/mock_backend.py`; the frontend is Maheksaba's.
- [ ] **Remove the Streamlit coupling from the backend path.** `utils/config.py` reads
      `st.secrets` and `st.session_state`. Split a pure `get_settings(overrides)` from a
      Streamlit-only `runtime_settings()`. Keep environment variable names unchanged.
- [ ] **Map the eight factors to the four SRS dimensions** (engagement, fit, intent, decision
      readiness), or ask for an SRS decision that eight factors satisfy FR-030. Adding a
      `dimension` field to `ScoreFactor` is the cleanest option.
- [ ] **Classify provider errors.** Retry only timeouts, connection errors, 429 and 5xx. Fail fast
      on 401/403 and on Pydantic validation errors. Pass a timeout to `genai.Client`.
- [ ] **Pin dependencies** and declare `google-genai` as an optional extra.
- [ ] **Add a LangGraph-present test** that asserts `build_workflow(provider) is not None` and
      checks the `trace` for each operation.
- [ ] **Enforce the transcript size limit** before building the conversation prompt.
- [ ] **Keep the honesty language.** Do not add a conversion probability to the heuristic score.

### Verification the PR must show

- [ ] `pytest -q` -> all tests pass (currently 17).
- [ ] With `SALES_GENIE_AI_BACKEND=external` and `SALES_GENIE_LLM_PROVIDER=mock`, the Team-C
      adapter returns validated output for:
      `analyze_lead`, `generate_outreach`, `summarize_conversation`, `recommend`,
      `score_lead`, `interpret_analytics`.
- [ ] No secrets in the diff.

### Interface the backend expects

```
ai.graph.run_workflow(operation, request, provider, checkpointer=None, thread_id=None)
    -> WorkflowResponse(result, research, qualification, execution, errors)

ai.providers.create_provider(settings) -> BaseLLMProvider
ai.providers.ProviderError

ai.scoring.rule_based.calculate_lead_score(
    lead, weights=None, qualified_threshold=70, nurture_threshold=45
) -> LeadScoreResult

utils.config.get_settings(overrides: dict | None = None) -> Settings
```

Operations: `research`, `lead_intelligence`, `outreach`, `conversation`, `follow_up`,
`sales_insights`.

---

## 3. Maheksaba Akbar Shaikh - frontend

**Target:** one PR to `Infosys-Spring-Team-C/Team-C`

The backend contract is documented in [`api-contract.md`](api-contract.md) and the hand-off
checklist in [`frontend-integration.md`](frontend-integration.md).

### Must do

- [ ] Build the Streamlit app in a new `frontend/` (or `ui/`) directory; do not overwrite backend
      files.
- [ ] Authenticate via `POST /api/v1/auth/token`; keep the token in session state.
- [ ] Use the documented endpoints; do not compute AI output client-side and do not store LLM keys
      in the frontend.
- [ ] Render `null` KPIs as "not defined", not zero.
- [ ] Show heuristic scores with `methodology_note`; never call them probabilities.
- [ ] Label demo/sample data visibly.
- [ ] Add a Compose `ui` service **only when the app exists**, and do not re-add a default password.

### Known contract gaps

- `PATCH /follow-ups/{id}` is not implemented; keep that list read-only.
- `GET /leads` has no `status` filter; use `stage`.
- `POST /outreach/send` returns `501` by design.

If a screen needs a change, open an issue against Team-C rather than adding a client-side
workaround that hides missing functionality.

---

## 4. Project lead - integration sequence

1. Merge the backend branch (this work) after review.
2. Merge Mahidhar's AI PR; set `SALES_GENIE_AI_BACKEND=external` in a staging environment and run
   the adapter smoke tests.
3. Merge Sai's database/CI PR after rebasing it onto the canonical migration.
4. Merge Maheksaba's frontend PR; run the end-to-end checklist.
5. Tag the milestone only after the Docker build and the external-AI path have been executed at
   least once.
