# PR Change List - what each contributor must change

This is the actionable version of [`contributor-actions.md`](contributor-actions.md): exact files,
exact changes, exact commands. Each contributor works in **their own fork of Team-C**, on their own
branch, under their own Git identity. Nobody copies anyone else's code.

**Merge order matters:** backend (done) -> AI (Mahidhar) -> database/CI (Sai) -> frontend
(Maheksaba). Later PRs rebase on earlier ones.

---

## 0. The way: one product, four attributable contributions

| Where | What it is | Who can commit |
|---|---|---|
| `Infosys-Spring-Team-C/Team-C` | The only runnable application | Everyone, via reviewed PRs from their own account |
| `Infosys-Spring-Team-C/team-c-mahi` | Mahidhar's portfolio repo (AI/ML) | Mahidhar only |
| `Infosys-Spring-Team-C/team_c_sai` | Sai's portfolio repo (database/DevOps) | Sai only |
| Maheksaba's repo | Frontend portfolio repo | Maheksaba only |

Rules that keep attribution honest:

1. **No squash-merging.** Use a merge commit (`gh pr merge --merge`) so each person's commits stay
   in `main` with their own author and date.
2. Each PR body links the author's portfolio repo and states which commits are theirs.
3. Portfolio repos are **not** second versions of the app. They hold the module plus a README
   section "Merged into Team-C" with the PR link.
4. Nobody edits another person's portfolio repo. Nobody pushes to `main` directly.

### Commands every contributor runs

```powershell
# 1. Fork Team-C on GitHub, then:
git clone https://github.com/<your-username>/Team-C.git
cd Team-C
git remote add upstream https://github.com/Infosys-Spring-Team-C/Team-C.git
git fetch upstream
git checkout -b <your-branch> upstream/main

# 2. make your changes, then:
git add -A
git commit -m "<type>(<area>): <summary>"
git push -u origin <your-branch>

# 3. open the PR against upstream main
gh pr create --repo Infosys-Spring-Team-C/Team-C `
  --base main --head <your-username>:<your-branch> `
  --title "<title>" --body-file pr-body.md
```

Branches: `feature/ai-package` (Mahidhar), `feature/db-ci-hardening` (Sai),
`feature/streamlit-frontend` (Maheksaba).

---

## 1. Mahidhar - `feature/ai-package`

### 1.1 What to add

Copy **only** these paths from `team-c-mahi`:

```
ai/                      all of it
utils/__init__.py
utils/config.py          after the split in 1.2
utils/logging.py
utils/validation.py
tests/ai/                your tests, moved (see 1.7)
requirements-ai.txt      new (see 1.6)
```

Append one line to `requirements.txt`: `-r requirements-ai.txt`

**Do not add:** `app.py`, `pages/`, `components/`, `services/`, `integrations/`, `.streamlit/`,
`.pytest_cache/`, `.venv/`, `assets/`, screenshots. The frontend belongs to Maheksaba.

### 1.2 `utils/config.py` - remove the Streamlit coupling  *(required)*

Today the backend imports `get_settings`, and that module also imports Streamlit:

| Line | Current | Change |
|---|---|---|
| 15-23 | `_secret()` falls back to `st.secrets` | Delete the Streamlit branch; read `os.environ` only |
| 65 | `get_settings(overrides=None)` | Keep the signature and every environment variable name exactly |
| 86-95 | `runtime_settings()` reads `st.session_state` | Move to a **new** `utils/streamlit_config.py` |

`backend/intelligence/external.py` calls `get_settings(overrides={...})` with the keys
`demo_mode`, `llm_provider`, `llm_model`, `llm_temperature`, `request_timeout_seconds`,
`grok_api_key`, `google_api_key`. Renaming any of them breaks the adapter.

Verify without Streamlit installed:

```powershell
python -c "import utils.config, inspect; print(inspect.signature(utils.config.get_settings))"
```

### 1.3 `ai/providers.py` - retry only transient failures  *(required)*

`structured()` (lines 30-45) currently retries **every** exception, including
`pydantic.ValidationError` and 401/403. That hides configuration errors and burns time.

* Retry: timeouts, connection errors, HTTP 429 and 5xx.
* Fail immediately: `ValidationError`, 401/403, malformed configuration.
* Keep the final `ProviderError` with the underlying message, and never include the API key.
* Add a test asserting a validation failure calls the provider exactly **once**.

### 1.4 `ai/providers.py` - Gemini timeout  *(required)*

Line 101 creates `genai.Client(api_key=...)` with no timeout, unlike `GrokProvider`. Pass an HTTP
timeout derived from `settings.request_timeout_seconds` through `http_options` (google-genai
expects milliseconds - check the API of the installed version). Do not hard-code a second value.

### 1.5 `ai/scoring/rule_based.py` - map 8 factors onto the SRS 4 dimensions  *(required)*

SRS FR-030 names four dimensions. Add to `ai/schemas.py`:

```python
dimension: Literal["Fit", "Intent", "Engagement", "Decision readiness"] | None = None
```

and set it in `_factor()`. Keep the existing weights (they already sum to 100):

| Factor | Weight | Dimension |
|---|---|---|
| `company_fit` | 20 | Fit |
| `industry_relevance` | 15 | Fit |
| `company_size` | 10 | Fit |
| `contact_role` | 15 | Decision readiness |
| `engagement_history` | 15 | Engagement |
| `explicit_needs` | 15 | Intent |
| `sales_stage` | 5 | Decision readiness |
| `response_behavior` | 5 | Engagement |

Result: Fit 45, Engagement 20, Decision readiness 20, Intent 15 - all four represented, and the
existing 8-factor explainability is preserved. Do **not** invent a conversion probability.

Team-C's contract ignores unknown fields today, so this merges safely. The project lead adds the
field to `backend/intelligence/contract.py` in a follow-up so the API can persist it.

### 1.6 `requirements-ai.txt` - pinned, AI only  *(required)*

```
langgraph==<pin>
openai==<pin>          # Grok transport
google-genai==<pin>    # optional Gemini
scikit-learn==<pin>    # only if EvaluatedSklearnLeadScorer is kept
```

Do **not** pin `pydantic` differently from Team-C (`2.14.1`); omit it and inherit. Do **not** add
`streamlit`, `pandas` or `plotly` - those are frontend dependencies.

### 1.7 Tests  *(required)*

* Move the suite to `tests/ai/` so it cannot collide with the backend tests.
* Keep all 17 passing.
* Add: retry classification (1.3), LangGraph-present assertion (`build_workflow(...) is not None`),
  and the `dimension` mapping.
* Run from the Team-C root: `pytest -q`.

### 1.8 Key names the adapter depends on  *(do not change)*

| Call | Required keys |
|---|---|
| `run_workflow("outreach", request, provider)` | `lead`, `channel`, `campaign_objective`, `company_insights`, `tone`, `product_service`, `call_to_action` |
| `run_workflow("lead_intelligence", ...)` | `lead` |
| `run_workflow("conversation", ...)` | `transcript`, `notes` |
| `run_workflow("follow_up", ...)` | `lead` |
| `run_workflow("sales_insights", ...)` | `analytics` |
| `calculate_lead_score(lead, qualified_threshold=, nurture_threshold=)` | as-is |

Optional: add `length` (`short`/`medium`/`long`) to the outreach prompt. The adapter currently
strips it because the package ignores it - if you add it, say so in the PR and the lead will
forward it.

### 1.9 Definition of done

- [ ] `pytest -q` green (backend 111 + your tests).
- [ ] `python scripts/check_ai_integration.py` prints `6/6 operations passed`.
- [ ] No Streamlit import in the backend path.
- [ ] No secrets, no `.env`, no `.venv`.
- [ ] PR body links `team-c-mahi` and lists your commits.

---

## 2. Sai - `feature/db-ci-hardening`

**Do not bring the schema.** Team-C already has the canonical eight tables, the migration and the
constraint tests. Her reduced column set would regress Modules 2-4, and two competing DDL sources
would drift. Her contribution is the operational layer, which is genuinely missing.

### 2.1 `.github/workflows/backend-ci.yml`  *(required)*

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
        with: { python-version: "3.11" }
      - run: pip install -r requirements-dev.txt
      - run: python -m alembic upgrade head
      - run: python -m pytest -q
```

`tests/test_postgres.py` drops and recreates the `public` schema and refuses databases whose name
does not contain `test`. The CI database is disposable, so that is safe.

### 2.2 `docs/operations-runbook.md`  *(required)*

Cover, with commands: backup (`pg_dump -Fc`), restore (`pg_restore --clean --if-exists`), retention
policy, `alembic upgrade head` / `current` / `downgrade`, what to do when a migration fails
mid-deploy, connection-pool sizing, and who to notify. No credentials in examples.

### 2.3 `scripts/backup_db.ps1` and `scripts/restore_db.ps1`  *(required)*

Read `DATABASE_URL`, fail fast when unset, write timestamped dumps to a caller-supplied directory,
never echo the password, refuse to restore over a non-empty database without `-Force`.

### 2.4 Optional `alembic/versions/0002_*.py`

Only if she can show the need with `EXPLAIN (ANALYZE, BUFFERS)` on realistic volume. Candidates:

* `outreach_campaigns(created_at)` - global activity trend scans;
* `sales_interactions(interaction_date)` - global interaction counts.

Rules: index-only change, explicit `downgrade()`, no column edits, no renames, and a note in the PR
with the query plan that motivated it. If the plan shows a sequential scan is fine at this scale,
**do not add the migration** - say so instead.

### 2.5 Do not include

`init_schema.sql`, any default password (`${POSTGRES_PASSWORD:-...}`), `container_name`, a second
Alembic head, her `src/database/models/*` (superseded), or port `5432` published on all
interfaces.

### 2.6 Definition of done

- [ ] CI green on the PR (this is the first CI run the repo will ever have).
- [ ] `alembic upgrade head` then `alembic downgrade base` succeed on PostgreSQL 16.
- [ ] Backup -> drop -> restore round trip demonstrated in the PR description.
- [ ] No secrets, no schema regression.

---

## 3. Maheksaba - `feature/streamlit-frontend`

| # | Change | Detail |
|---|---|---|
| F-1 | Add `frontend/` only | No edits to `backend/`, `alembic/`, `tests/` |
| F-2 | `requirements-frontend.txt` | `streamlit`, `requests`, `pandas`, `plotly`, pinned |
| F-3 | Auth | `POST /api/v1/auth/token`, token in `st.session_state`, `Authorization: Bearer` on every call, 401 clears the session |
| F-4 | Generation | Call `POST /leads/{id}/insights`, `/outreach/generate`, `/scores`, `/conversations/summarize`. Never compute AI output client-side; never hold an LLM key |
| F-5 | Dashboard | `null` + `pending_definition: true` renders as "Not defined", never `0` |
| F-6 | Compose | Add a `ui` service **only** once `frontend/app.py` exists, with no default password |
| F-7 | Honesty | Show `methodology_note` beside scores; show `missing_or_uncertain` for summaries |

Contract: [`api-contract.md`](api-contract.md). Checklist: [`frontend-integration.md`](frontend-integration.md).

---

## 4. What the project lead changes in Team-C to accept each PR

| When | Change | Reason |
|---|---|---|
| Mahidhar merges | Add `dimension: str \| None = None` to `ScoreFactor` in `backend/intelligence/contract.py`; persist it in `routers/scoring.py`; document in `api-contract.md` | Surfaces the SRS 4-dimension mapping |
| Mahidhar merges | Verify `requirements-ai.txt` is pulled in by `requirements.txt`; rebuild the image | Docker must install the AI deps |
| Mahidhar merges | Run `python scripts/check_ai_integration.py`; flip `SALES_GENIE_AI_BACKEND=external` only in a staging `.env` | Proves the adapter before claiming it |
| Sai merges | Confirm CI is green, then make it a required check | Prevents future breakage |
| Maheksaba merges | Add the `ui` service, re-run the end-to-end checklist | Frontend only exists then |
| After all three | Update `README.md` status table, `docs/test-report.md`, `docs/milestone-readiness.md`; tag `v1.0-milestone` | Documentation must match reality |

`scripts/check_ai_integration.py` is already in this branch, so it is available the moment the AI
PR lands.

---

## 5. Merge commands (project lead)

```powershell
git checkout main
git pull upstream main

gh pr merge <ai-pr-number>   --repo Infosys-Spring-Team-C/Team-C --merge
git pull
python -m pytest -q
python scripts/check_ai_integration.py      # must print 6/6

gh pr merge <db-pr-number>   --repo Infosys-Spring-Team-C/Team-C --merge
gh pr merge <ui-pr-number>   --repo Infosys-Spring-Team-C/Team-C --merge

docker compose up --build
python -m pytest -q
git tag -a v1.0-milestone -m "Backend, AI, database/CI and frontend integrated"
git push origin v1.0-milestone
```

Use `--merge`, not `--squash`. If the organisation forces squash, add `Co-authored-by:` trailers so
the individual commits remain discoverable, and link each PR in the portfolio README.

---

## 6. Presentation split - what each person shows

| Presenter | Repo to show | Demo | Do not claim |
|---|---|---|---|
| Isharak (lead) | `Team-C` | Login -> import CSV -> insights -> outreach -> score -> dashboard; `/docs`; RBAC 403s | That Docker/AI/frontend were verified if they were not |
| Mahidhar | `team-c-mahi` + his merged PR | `pytest -q` (17+), agent graph and prompts, the 8->4 dimension mapping, mock vs real provider | Accuracy metrics, a trained model, or a conversion probability |
| Sai | `team_c_sai` + her merged PR | ER diagram, schema rationale, CI run, backup/restore round trip, query plan | That her original schema was merged as-is |
| Maheksaba | her repo + merged PR | UI walkthrough against the live API | That the UI computes AI, or that e-mail is sent |

Each portfolio README should gain one section:

```markdown
## Merged into Team-C
- Pull request: <link>
- My commits: <git log --author="<name>" --oneline upstream/main>
- What I owned: <one paragraph>
- What I would do next: <one paragraph>
```

That is what makes the individual work "stand": a merged PR, a commit range, and a repo that
explains the module - without a second copy of the product.
