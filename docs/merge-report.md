# Milestone 2 consolidation report

Date: 5 November 2026
Scope: combine the backend (`team-c-doran`), AI/DevOps (`team-c-mahi`) and database
(`team_c_sai`) contributions into the canonical Team-C tree, make the AI package the
default intelligence engine, finish the Outreach Studio, and prepare the Milestone 2
review.

See [`CREDITS.md`](../CREDITS.md) for contributor attribution.

---

## 1. Baseline

The canonical Team-C tree already contained:

- the FastAPI backend, JWT/RBAC, Alembic schema and test suite;
- Mahek's Streamlit frontend with an `api_compat.py` boundary;
- Mahidhar's `ai/` package and `utils/` modules;
- an `ExternalAIEngine` adapter, but AI was **opt-in** via
  `SALES_GENIE_AI_BACKEND=external`;
- a heuristic engine used by default.

Baseline verification before changes:

```
149 passed, 7 skipped
scripts/check_ai_integration.py: 6/6 operations passed (external + mock)
```

## 2. Merge decisions

### 2.1 AI package (Mahidhar)

Kept the merged package in `ai/` and `utils/`. Team-C's `ai/providers.py` and
`ai/scoring/models.py` are newer than the submitted archive and were kept, so the
archive was not re-applied over them.

Changes made for the product path:

| Change | File |
|---|---|
| Default engine is `auto`; AI package wins when importable | `backend/config.py`, `backend/intelligence/__init__.py` |
| Default provider is `auto`: OpenAI, then Gemini, then mock | `backend/intelligence/external.py` |
| Provider/model auto-resolution and truthful `used_mock` | `backend/intelligence/external.py` |
| Forward `length`; add regeneration section rotation | `backend/intelligence/external.py`, `backend/schemas.py` |
| Mock provider honours short/medium/long length | `ai/agents/outreach.py` |
| Prompt documents channel/tone/length | `ai/prompts/templates.py` |
| Aggregate 8 AI factors into the 4 SRS dimensions before persistence | `backend/routers/scoring.py` |
| Health endpoint exposes `ai_provider`, `ai_model`, `ai_used_mock`, `ai_mode`, `ai_status` | `backend/api.py` |

The heuristic remains selectable and tested; it is no longer the default. If the AI
package is missing, `auto` falls back to the heuristic and reports it. If `external`
is requested explicitly, a missing package still fails loudly instead of silently
changing engines.

### 2.2 Backend + CRM (Doran)

Doran's repository is a smaller independent backend with different model names
(`Lead.lead_id`, `lead_status`, `revenue`). Replacing the canonical backend would
have discarded authentication, migrations, analytics and the QA suite, so the
canonical backend was retained.

Unique work merged and adapted:

- `backend/services/crm.py`: provider-neutral payload mapping and deterministic
  simulator derived from Doran's `app/services/crm_service.py`. Uses canonical
  columns (`lifecycle_stage`, `annual_revenue`, `owner_id`).
- `POST /api/v1/crm/sync` accepts `"simulate": true`, persists a `CRMSyncLog` with
  `mode=simulated`, returns per-lead records, and explicitly states that no CRM
  request was made. The default request without `simulate` remains `501`
  (`crm_not_configured`), preserving SRS D-06.
- `GET /api/v1/crm/status` reports connectivity `simulated`, recent sync counts and
  failure rate.

### 2.3 Database (Sai)

Sai's `salesgenie-db-workspace/` remains the database deployment baseline. The
canonical Alembic schema and `backend/db.py` already reconcile her eight tables and
expand them for authentication and audit columns. No destructive re-application was
performed; the rationale is recorded in `docs/database-merge-notes.md`.

### 2.4 Frontend (Mahek)

Kept Mahek's Streamlit UI. Integration work added in `frontend/`:

- Prompt controls: length, outreach type, goal, industry context, pain points,
  product/service and call to action.
- Generation payload now sends every control; the returned draft id, status and AI
  execution metadata are retained.
- “Regenerate Variation” increments a variant so the deterministic provider rotates
  the rewritten section.
- Removed the fabricated default score of `75`; an unscored lead now shows
  **Not scored** and strategy copy that refuses to invent priority.
- Save Draft (create or patch) and Record as Sent (status only, no transmission).
- Copy block retained; dispatch attempts truthfully report the `501`.
- Sidebar and hero show the actual AI engine/provider/model and warn when the mock
  provider is in use.

### 2.5 Demo data

`python -m backend.cli seed-demo --confirm` now creates six clearly fictional leads
with industry, size, revenue, funding, tech stack, role, explicit needs, engagement
history, response behaviour, user research and pain points. The seed is idempotent on
`email_key`.

## 3. Test and verification evidence

Commands run from the repository root with the local virtual environment:

```
.venv/bin/python -m pytest -q
159 passed, 7 skipped, 1 warning in 21.42s
```

```
.venv/bin/python scripts/check_ai_integration.py
PASS analyze_lead: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS generate_outreach: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS summarize_conversation: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS recommend: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
PASS score_lead: engine=external provider=mock model=rule-based used_mock=False score=82 factors=8 probability=None
PASS interpret_analytics: engine=external provider=mock model=deterministic-demo-v1 used_mock=True
6/6 operations passed
```

New coverage in `tests/test_merge_integration.py`:

- auto engine selects the AI package with mock when no key is configured;
- auto engine falls back to the heuristic when the package is missing;
- eight AI factors aggregate to `fit/intent/engagement/decision readiness`;
- heuristic four-factor scores are kept verbatim;
- CRM simulation is labelled and audited; `/crm/status` reports it;
- CRM simulation requires at least one lead id;
- health exposes non-secret AI metadata;
- rich demo seed is idempotent and populated.

Updated coverage in `tests/test_external_adapter.py`:

- `length` is forwarded to the package;
- `variant` rotates the regenerated section;
- provider `auto` resolves OpenAI, then Gemini, then mock.

## 4. Environment used

- Python 3.14 in `.venv` (created for this consolidation).
- SQLite for the test suite and the local demo.
- No OpenAI, Gemini, Grok or Anthropic key present; no Ollama installed.
- No `git` or `gh` binary available; no GitHub credentials. Changes exist only in
  this working tree.

## 5. Known gaps carried forward

1. Live OpenAI/Gemini calls remain unverified. The mock path is complete and labelled.
2. Email delivery is still `501` by design.
3. `conversion_probability` is still `null`; no calibrated model exists.
4. CRM transport is simulated only.
5. The consolidation is uncommitted. Push it with contributor authorship before
   presenting commit history as evidence.
