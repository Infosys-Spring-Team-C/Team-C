# Team-C AI layer handoff

This document describes the framework-independent AI intelligence layer
contributed for Team-C integration.

> **Maintainer note (Team-C lead).** This work reached the repository as a
> submitted archive, not as a pull request: the contributor could not push a
> branch or open a PR. It is committed with the contributor as *author* and the
> maintainer as *committer* (`feat(ai)` and `test(ai)` commits). The integration
> corrections listed at the end of this file were applied by the maintainer in
> follow-up commits and are not the contributor's work.

## In scope

- All modules under `ai/`: graph/state, agents, prompts, provider boundary,
  schemas, and rule-based scoring.
- The shared, non-Streamlit utility modules under `utils/`: `__init__.py`,
  `config.py`, `csv_import.py`, `logging.py`, and `validation.py`.
- `ai/requirements.txt`: AI runtime dependencies. Versions are currently
  expressed as compatible ranges.

## Excluded from this change

`app.py`, `pages/`, `components/`, and `services/` are Streamlit/presentation
or backend-client code and are not part of this handoff.

## Integration follow-ups intentionally left for the branch owner

- Remove the optional Streamlit secrets/session coupling from `utils/config.py`.
- Make retry and timeout behavior explicit in `ai/providers.py` for every provider.
- Map the eight factors in `ai/scoring/rule_based.py` to the SRS's four dimensions.
- Pin exact versions in `ai/requirements.txt`.

No integration fixes have been applied in this push.

## What Team-C actually imported

Only the parts the backend needs were taken from the archive:

- `ai/` (graph, agents, prompts, providers, schemas, scoring).
- `utils/__init__.py`, `utils/config.py`, `utils/logging.py`.
- `tests/test_workflows.py`, `tests/test_scoring.py`,
  `tests/test_prompts_and_schemas.py` (from the same submitted repository).

`utils/csv_import.py` and `utils/validation.py` were **not** imported: Team-C
already has `backend/services/csv_import.py` and its own validation layer, and
`ai/` does not import either module. Keeping them would create the same
two-implementations problem that the database merge had to undo.

## Integration corrections applied by the maintainer

1. `backend/intelligence/external.py` no longer passes `grok_api_key` into the
   package `Settings` (which has no such field) and rejects
   `SALES_GENIE_LLM_PROVIDER=grok` with the external engine explicitly.
2. `utils/config.py` reads secrets from the environment only; Streamlit is
   touched only by `runtime_settings()` for non-secret UI preferences.
3. `ai/providers.py` retries only transient failures (timeout, 429, 5xx) and
   Gemini now receives the configured request timeout.
4. `ScoreFactor` gained an optional `dimension` field, and the adapter maps the
   eight package factors onto the SRS FR-030 dimensions (fit, intent,
   engagement, decision readiness) without changing the package's score.
5. `ai/requirements.txt` now pins exact verified versions; the unused
   `scikit-learn` dependency was dropped and the optional `numpy` import in
   `ai/scoring/models.py` is lazy.
6. The LangGraph checkpointer test skips cleanly when the optional `langgraph`
   extra is not installed.

