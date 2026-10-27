# Team-C AI layer handoff

This PR hands off the framework-independent AI intelligence layer for Team-C
integration. The existing Python modules are intentionally unchanged; this PR
adds scope notes and the AI-only dependency list.

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
