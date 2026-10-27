# AI / ML Review - `team-c-mahi`

**Reviewer:** Mohamed Isharak M
**Repository:** `https://github.com/Infosys-Spring-Team-C/team-c-mahi`
**Commit reviewed:** `dbec717` (`Delete .venv directory`)
**Status:** review only. No files were modified in Mahidhar's repository.

The reviewed package must reach Team-C through Mahidhar's own pull request so the work remains
attributed to him. Team-C does **not** copy `ai/` or `utils/`; it defines an adapter and a typed
contract. See `backend/intelligence/external.py` and `backend/intelligence/contract.py`.

> **Update, 27 October 2026 - integration completed.** The contributor could not push a branch
> or open a PR, so his archive was applied with him as git *author* and the lead as
> *committer*. See `docs/ai-handoff.md` for the disclosure and the list of maintainer
> corrections. Resolution of the findings below:
>
> | Finding | Status |
> |---|---|
> | A-01 package absent | **Closed** - `ai/` merged, gate 6/6 |
> | A-02 no persistence | **Closed by design** - the backend owns persistence; the package does not |
> | A-03 eight factors vs four dimensions | **Closed** - `ScoreFactor.dimension` maps all eight onto fit/intent/engagement/decision readiness |
> | A-04 Streamlit coupling in `utils/config.py` | **Closed** - environment-only secrets; Streamlit confined to `runtime_settings()` |
> | A-05 unclassified provider errors, no Gemini timeout | **Closed** - transient-only retries; Gemini receives the configured timeout |
> | A-06 no conversion-probability model | **Open by design** - `conversion_probability` stays `null`; this is a truthful limitation |
> | A-07 LangGraph fallback can hide defects | **Mitigated** - checkpointer test runs when the extra is installed and skips otherwise |
> | A-08 `run_workflow` collects errors | **Accepted** - the adapter raises `IntelligenceError` when `errors` is non-empty |
> | A-09 unbounded context | **Mitigated** - `max_transcript_chars` chunking retained |
> | A-10 dependencies incomplete/unpinned | **Closed** - exact pins; `scikit-learn` dropped; `numpy` import is lazy |
> | A-11 outreach request keys | **Closed** - the adapter translates `outreach_type`/`goal`/`pain_points` |

---

## 1. Verified execution

The repository was cloned to an isolated directory and given its own virtual environment.

```
$ python -m pytest -q
.................                                                        [100%]
17 passed in 1.40s
```

Dependencies installed for the run: `pydantic`, `pytest`, `httpx`, `python-dotenv`, `numpy`,
`langgraph`, `openai`. The pass is genuine; the tests do not require an API key because the
deterministic mock provider is used.

**Caveat:** a passing unit suite is not evidence that real model calls work. No provider was
called during this review.

---

## 2. Component inventory

| File | Public interface | Status | Inputs / outputs | Backend integration point |
|---|---|---|---|---|
| `ai/graph.py` | `run_workflow(operation, request, provider, checkpointer=None, thread_id=None) -> WorkflowResponse` | Working; LangGraph with a non-LangGraph fallback | operation string + request dict -> validated result + execution record | `ExternalAIEngine._run` |
| `ai/state.py` | `WorkflowState` TypedDict | Working | graph state | internal |
| `ai/schemas.py` | Pydantic boundary models | Working, well designed | structured AI output | mirrored by `backend/intelligence/contract.py` |
| `ai/providers.py` | `create_provider(settings)`, `BaseLLMProvider.structured()` | Working; mock + OpenAI + Gemini (no Grok provider exists) | prompt + response model -> validated model | `ExternalAIEngine.__init__` |
| `ai/agents/research.py` | `analyze_lead_context(request, provider)` | Working | lead context -> `ResearchResult` | `analyze_lead` |
| `ai/agents/qualification.py` | `qualify_lead(request, research, provider)` | Working | research -> `QualificationAssessment` | `analyze_lead` |
| `ai/agents/outreach.py` | `generate_outreach(request, provider)` | Working | lead + parameters -> `OutreachDraft` | `generate_outreach` |
| `ai/agents/conversation.py` | `summarize_conversation(request, provider)` | Working | transcript/notes -> `ConversationSummary` | `summarize_conversation` |
| `ai/agents/follow_up.py` | `recommend_follow_up(request, provider)` | Working | lead -> `Recommendation` | `recommend` |
| `ai/agents/sales_insights.py` | `interpret_sales_analytics(analytics, provider)` | Working | aggregates -> `SalesInsightsResult` | `interpret_analytics` |
| `ai/prompts/templates.py` | `build_prompt(task, context, response_model)` | Working; explicit prompt-injection defences | task + context -> system/user prompts | unchanged |
| `ai/scoring/rule_based.py` | `calculate_lead_score(lead, weights=None, qualified_threshold=70, nurture_threshold=45)` | Working, deterministic | lead dict -> `LeadScoreResult` | `score_lead` |
| `ai/scoring/models.py` | weight definitions | Working | - | - |
| `utils/config.py` | `get_settings(overrides=None)`, `runtime_settings()` | Working **but Streamlit-coupled** | env / `st.secrets` / session state -> `Settings` | replaced by `backend/config.py` |
| `utils/logging.py` | `get_logger(name)` | Working | - | unchanged |
| `utils/validation.py` | validation helpers | Working | - | unchanged |
| `services/api_client.py` | Streamlit HTTP client | Working | UI -> backend | not imported by backend |
| `integrations/backend_adapter.py` | demo/live adapter | Working | UI -> backend or in-memory | not imported by backend |
| `integrations/mock_backend.py` | in-memory demo backend | Working, clearly labelled | - | not used by backend |

The temporary Streamlit app (`app.py`, `pages/`, `components/`) is **not** the final frontend and
must not be merged as a replacement for Maheksaba's work.

---

## 3. Findings

### A-01 (High) - Package is absent from Team-C

`Team-C/backend/api.py` at commit `f3724a2` imported `ai.providers`, `ai.graph` and `utils.config`,
none of which exist in Team-C. This is the direct cause of the baseline
`ModuleNotFoundError: No module named 'ai'`.

**Resolution in Team-C.** The import was removed from the API layer. The adapter imports the
package lazily and raises a clear `IntelligenceError` if it is missing:

```
SALES_GENIE_AI_BACKEND=external was requested but the reviewed AI package
(ai.* / utils.*) is not installed in this checkout. Merge the AI pull request
or set SALES_GENIE_AI_BACKEND=heuristic.
```

**Required action.** Mahidhar opens a PR adding `ai/` and the non-Streamlit parts of `utils/`.
Until it is merged, `SALES_GENIE_AI_BACKEND=heuristic` keeps the backend runnable.

---

### A-02 (High) - No persistence or backend

The repository is an AI library plus a Streamlit demo. Scores, insights, drafts and summaries are
held in Streamlit session state and lost on restart. SRS FR-017, FR-031, FR-040 and FR-047 require
persistence.

**Resolution in Team-C.** The backend persists every AI result:

| AI output | Table |
|---|---|
| Research + qualification | `company_insights` |
| Outreach draft | `outreach_campaigns` |
| Score + factors | `lead_scores` |
| Conversation summary | `sales_interactions` |
| Analytics interpretation | returned; snapshot table available |

**Required action.** None from Mahidhar - persistence is backend-owned. He should not add a
database layer to `ai/`.

---

### A-03 (Medium) - Eight score factors vs four required dimensions

`ai/scoring/rule_based.py` defines:

```python
DEFAULT_WEIGHTS = {
    "company_fit": 20, "industry_relevance": 15, "company_size": 10, "contact_role": 15,
    "engagement_history": 15, "explicit_needs": 15, "sales_stage": 5, "response_behavior": 5,
}
```

SRS FR-030 names four dimensions: engagement, company fit, intent and decision readiness. The
eight-factor model is not wrong - it is more granular - but it cannot be reported as the four
required dimensions without a mapping.

**Resolution in Team-C.** The shipped heuristic uses exactly four factors with weights 30/25/25/20.
When the external engine is enabled, the adapter accepts eight factors and persists them as-is, so
the UI would show eight cards rather than four.

**Required action.** Choose one:

1. Add a `dimension` field to `ScoreFactor` and map the eight factors onto the four SRS dimensions;
   or
2. Ask the project lead to record an SRS decision that eight factors satisfy FR-030.

Option 1 is recommended because it preserves the richer model and satisfies the requirement.

---

### A-04 (Medium) - `utils/config.py` is coupled to Streamlit

```python
def _secret(name, default=""):
    ...
    import streamlit as st
    return str(st.secrets.get(name, default))

def runtime_settings():
    import streamlit as st
    allowed = st.session_state.get("salesgenie_runtime_config", {})
```

A backend must not read browser session state. Team-C therefore owns `backend/config.py` and passes
explicit `overrides` into `utils.config.get_settings(overrides=...)` from the adapter. That works
because the Streamlit imports are inside `try/except`, but it is fragile.

**Required action.** Split `utils/config.py` into:

* a pure `get_settings(overrides)` with no Streamlit import, and
* a Streamlit-only `runtime_settings()` in the frontend package.

Keep the environment variable names unchanged so the adapter does not need edits.

---

### A-05 (Medium) - Provider error handling is broad but not classified

`BaseLLMProvider.structured()` retries **any** exception (validation errors, authentication
failures, 4xx responses) with exponential backoff. Retrying a 401 or a schema violation wastes
time and can mask configuration errors. `GeminiProvider` creates `genai.Client(api_key=...)`
without a request timeout, while Grok passes `timeout=settings.request_timeout_seconds`.

**Required action.**

* Retry only transient failures (timeouts, connection errors, 429, 5xx).
* Raise immediately on 401/403 and on Pydantic validation errors after one attempt.
* Pass a timeout to the Gemini client.
* Surface the provider's error message without leaking the API key.

Team-C's adapter already converts any raised `ProviderError` into `502 ai_failed` and never
retries at the HTTP layer, so a fix in `ai/` is sufficient.

---

### A-06 (Medium) - No conversion-probability model

`ai/schemas.py` deliberately has no probability field and the methodology note says the score is
"not a predicted conversion probability". This is the honest position and matches SRS D-10.

However, Module 4 asks for "conversion-probability outputs". The backend therefore returns:

* `conversion_probability: null` (persisted as `NULL`),
* `probability_band: "low" | "medium" | "high"` with an explicit note that it is uncalibrated.

**Required action.** Do not add a fake probability. If a calibrated model is later trained, add a
separate service with documented training data, calibration method and measured metrics.

---

### A-07 (Low) - LangGraph fallback can hide graph defects

If `langgraph` is not installed, `build_workflow()` returns `None` and `_fallback_execute()` runs a
different code path with the same routing. The 17 tests pass either way, so a broken graph could go
unnoticed in CI if LangGraph is missing.

**Required action.** Add one test that asserts `build_workflow(provider)` is not `None` when
`langgraph` is installed, and assert the expected `trace` for each operation.

---

### A-08 (Low) - `run_workflow` swallows exceptions into `errors`

Node exceptions are caught and appended to `state["errors"]`; `run_workflow` then returns a
`WorkflowResponse` with `success=False`. That is good for UI resilience, but callers must check
`errors`. Team-C's adapter does and raises `IntelligenceError`, which becomes `502`.

**Required action.** Document in the package README that `errors` is authoritative and that
`result` may be `None` when `errors` is non-empty. (Already true in code.)

---

### A-09 (Low) - Prompt-injection defences are good, but context size is unbounded

`ai/prompts/templates.py` correctly delimits untrusted context with `--- DATA START ---` /
`--- DATA END ---` and instructs the model to ignore embedded instructions. That is a genuine
strength. However, `build_prompt` serialises the entire context with no size guard. A very long
transcript can exceed the model context window.

**Required action.** Enforce `settings.max_transcript_chars` in `conversation.py` before building
the prompt (the setting exists but the enforcement point should be explicit), and truncate with a
visible note.

---

### A-10 (Low) - Dependency list is incomplete/unpinned

`requirements.txt` does not pin versions, and `google-genai` is optional but not declared as an
extra. Reproducibility depends on the ambient environment.

**Required action.** Pin versions and document optional extras, for example:

```
pydantic==...
langgraph==...
openai==...          # Grok transport
google-genai==...    # optional Gemini
```

---

### A-11 (Medium) - Outreach request keys differ from the frontend contract

`ai/agents/outreach.py` reads its parameters as:

```python
channel = request.get("channel", "Email")
objective = request.get("campaign_objective", "start a discovery conversation")
user_insights = request.get("company_insights", lead.get("user_research", ""))
```

The backend API speaks `outreach_type`, `goal` and `pain_points` (see `docs/api-contract.md`).
Passing the request through unchanged would silently drop the user's choices: every external draft
would be an e-mail with the default objective, regardless of what was selected in the UI.

**Resolved in the adapter.** `ExternalAIEngine._outreach_payload()` translates the request:

| Backend field | AI package field |
|---|---|
| `outreach_type` | `channel` (`cold_email`/`follow_up` -> `Email`, `linkedin_message` -> `LinkedIn`, `call_script` -> `Call script`, `short_message` -> `Short message`) |
| `goal` | `campaign_objective` |
| `pain_points` + `industry` + `lead.user_research` | `company_insights` (joined text) |
| `tone`, `product_service`, `call_to_action` | passed through unchanged |

`length` (`short`/`medium`/`long`) has **no equivalent** in the package - its prompt has no length
control - so it is not forwarded. With the heuristic engine it is honoured; with the external
engine it is ignored. This is recorded as a limitation, not hidden.

**Optional action for Mahidhar.** If length control is wanted, add a `length` instruction to the
outreach prompt and expose it in `generate_outreach`. The adapter already sends nothing that would
conflict with such an addition.

This behaviour is covered by `tests/test_external_adapter.py`, which uses a stub implementing the
documented interface (not a copy of the package).

---

## 4. Interface mapping used by the backend adapter

`backend/intelligence/external.py` maps the package to the backend contract without copying code.

| Backend contract method | AI package call | Validation |
|---|---|---|
| `analyze_lead(lead)` | `run_workflow("lead_intelligence", {"lead": lead}, provider)` | `ResearchResult` + `QualificationAssessment` -> `LeadIntelligence` |
| `generate_outreach(lead, request)` | `run_workflow("outreach", translated_request, provider)` - see A-11 | `OutreachDraft` |
| `summarize_conversation(transcript, notes)` | `run_workflow("conversation", {...}, provider)` | `ConversationSummary` |
| `recommend(lead)` | `run_workflow("follow_up", {"lead": lead}, provider)` | `Recommendation` |
| `score_lead(lead)` | `calculate_lead_score(lead, qualified_threshold=..., nurture_threshold=...)` | `LeadScoreResult` (probability stays `None`) |
| `interpret_analytics(analytics)` | `run_workflow("sales_insights", {"analytics": analytics}, provider)` | `SalesInsightsResult` |

Every call returns `(validated_model, ExecutionInfo)`. `ExecutionInfo` records engine, provider,
model, duration and whether a mock was used. A missing package or invalid output raises
`IntelligenceError`; the API returns `502 ai_failed` and never silently falls back to another
engine.

---

## 5. Frontend contract differences to resolve

Mahidhar's `docs/backend_api_contract.md` assumes the Streamlit app computes AI output and posts it
to the backend for saving:

```
POST /leads/{id}/insights   {research, qualification, execution}
POST /leads/{id}/scores     {score, weights, method}
```

Team-C deliberately inverts this: the backend owns the AI call so that API keys never live in the
browser and outputs are always validated server-side.

| Mahidhar contract | Team-C implementation | Action |
|---|---|---|
| `POST /leads/{id}/insights` saves client-produced research | Generates server-side; ignores unknown body fields | Frontend calls it with an empty/optional body, then reads the response |
| `POST /leads/{id}/scores` saves a client score | Generates server-side | Frontend calls it with no body |
| `PATCH /follow-ups/{id}` | Not implemented; `/follow-ups` is derived from stored scores | Needs a recommendations table and an SRS decision; not built |
| `GET /leads?status=...` | Supports `query`, `stage`, `industry`; `status` is derived in responses | Add a `status` filter alias or update the frontend |
| `Lead.stage` values `"Closed Won"` / `"Closed Lost"` | Canonical values are `"converted"` / `"lost"`; aliases accepted on input | Frontend maps canonical values for display |
| `POST /leads/import` expects `{imported, skipped, errors}` | Returns `imported`, `duplicates`, `invalid`, `skipped` (computed), `errors` | Compatible |

These are documented for Maheksaba in [`frontend-integration.md`](frontend-integration.md). They
are contract decisions, not defects in Mahidhar's AI code.

---

## 6. Definition of done for Mahidhar's PR

- [ ] Branch from current Team-C `main`.
- [ ] Add `ai/` and the non-Streamlit parts of `utils/`.
- [ ] Do **not** add `app.py`, `pages/`, `components/` or `integrations/mock_backend.py`.
- [ ] `utils/config.py` no longer imports Streamlit in the backend path (or a pure split is
      provided).
- [ ] Pin dependencies; declare optional extras.
- [ ] Add the four-dimension mapping or attach the SRS decision (A-03).
- [ ] Classify retryable vs non-retryable provider errors; add Gemini timeout (A-05).
- [ ] Add the LangGraph-present test (A-07).
- [ ] All existing 17 tests still pass; new tests pass.
- [ ] With `SALES_GENIE_AI_BACKEND=external` and `SALES_GENIE_LLM_PROVIDER=mock`, the Team-C
      adapter smoke test returns validated output for all six operations.
- [ ] No secrets in the diff.
