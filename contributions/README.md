# Team contributions

This folder preserves standalone deliverables supplied by Team C members so the
work is attributed, reviewable and never lost when the canonical tree changes.
It is intentionally additive: nothing here replaces the integrated application
in `backend/`, `frontend/` or `ai/`.

| Folder | Contributor | Email | Source |
|---|---|---|---|
| `mahidhar-ai-layer/` | Mahidhar Reddy | mahidarreddy.2005@gmail.com | `ai-layer.zip` |
| `mahek-frontend-milestone3/` | Mahek Saba Shaikh | shaikh.akbar86691@gmail.com | `Infosys_TeamC_Frontend_Milestone3_Mahek_Saba_Shaikh.zip` |
| `team-c-doran/` | M. Doran | doranmallidi123@gmail.com | `team-c-doran` repository snapshot |

## M. Doran — backend contribution

`team-c-doran/` preserves the standalone FastAPI backend repository and its
milestone reports as an attributable source snapshot. The canonical application
remains in `backend/`; CRM work from this backend was adapted there, and the
standalone snapshot is retained for review and contribution provenance.

Verification (17 November 2026): running `python -m pytest -q` inside this folder
gives **24 passed, 1 failed**. The failure is
`tests/test_leads.py::test_delete_lead`, which calls the protected
`DELETE /leads/{lead_id}` route without a token and expects `204` but receives
`401`. It is recorded as BUG-020 in `docs/qa/bug-log.md` and left as an owner
action; the canonical suite is unaffected.

## Mahidhar Reddy — AI/ML layer

The `sales_intel` package is the standalone DealFlow AI layer (v0.3.0):

* transparent lead scoring with four dimensions and a weight tuner;
* a next-best-action engine with cadence, channel mix and guardrails;
* conversation summarisation;
* sample data, tuning reports and its own pytest suite.

The canonical application integrates the AI work through the `ai/` package and
`backend/intelligence/external.py` (six validated operations, provider
selection and `used_mock` labelling). `sales_intel` is kept here as the original
AI/ML deliverable and as the reference for the scoring tuner and NBA engine,
which are not yet wired into the canonical API. Its tests run from this folder:

```bash
cd contributions/mahidhar-ai-layer
pip install -r requirements.txt
python -m pytest -q
```

## Mahek Saba Shaikh — Milestone 3 frontend

This is the standalone frontend snapshot for Module 5 and the wider Streamlit
application:

* `modules/module5_conversation.py` — meeting summary, action items and stored
  interactions;
* the full Streamlit application, sample data and configuration;
* the internship technical report, screenshots and report generators.

The canonical UI in `frontend/` is the integrated peach-and-cream client that
talks to the FastAPI backend through `frontend/api_compat.py`. This snapshot is
kept as the design/report deliverable and as a reference for the Module 5
screens; it uses its own SQLite models and is not wired to the canonical API.

## Attribution policy

Commits that add or update a contributor's folder use that contributor as the
Git author. Integration work in the canonical tree remains attributed through
`CREDITS.md` and `docs/ai-handoff.md`.
