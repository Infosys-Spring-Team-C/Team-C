# Credits and contribution provenance

SalesGenie AI — Infosys Springboard Team C
Milestone 2 consolidation, 5 November 2026

This file records who contributed which parts of the project and how their work was
integrated. It complements the per-file reviews in `docs/` and the merge notes in
`docs/merge-report.md`.

> **Provenance.** The team repositories are private and no contributor had push access
> from this machine. The work was supplied as repository archives and consolidated into
> this working tree. No GitHub commits or pull requests could be created here; the
> attribution below is therefore the authoritative record until the tree is pushed by
> someone with write access. Nothing in this file upgrades unverified work into verified
> work.

---

## Contributors

### Maheksaba "Mahek" Akbar Shaikh — Frontend Engineer

Owns the Streamlit presentation layer.

- Lead management screens, CSV/manual lead entry, filtering and the executive dashboard.
- The Outreach Studio workflow: generate, refresh, edit, copy and send/record.
- Lead score cards, score badges, intent metrics and the Outreach Strategy panel.
- Theme, navigation and the visual design system in `frontend/app.py`.

Integrated as `frontend/` (from her `frontend-ui` branch) plus the
`frontend/api_compat.py` boundary that translates her UI contract onto the canonical
`/api/v1` backend. The latest Team-C main archive includes a full peach-and-cream
rewrite of `frontend/app.py`, `frontend/theme.py` and the login/normaliser layer; that
rewrite is the current UI baseline. In this consolidation the Outreach Studio received
the missing prompt controls (tone, length, outreach type, goal, industry, pain points,
product/service, CTA), regeneration, honest “not scored” handling, save/mark-sent
actions, draft status/execution labels and a truthful dispatch refusal. Those additions
are maintainer integration work, not a claim that Mahek supplied them or that she
personally wrote every line of the rewrite.

### Mahidhar (Mahi) — AI/ML and DevOps Engineer

Owns the AI intelligence package.

- `ai/`: LangGraph operation router, agents (research, qualification, outreach,
  conversation, follow-up, sales insights), Pydantic schemas, prompts, provider
  boundary (mock/OpenAI/Gemini), retry/timeout handling and rule-based scoring.
- Framework-independent `utils/`: settings, logging, CSV import and validation.
- AI tests and the provider/configuration documentation.
- DevOps handoff: AI dependency/configuration guidance reflected in the deployment
  files.

The package was merged into Team-C with Mahidhar as author and the maintainer as
committer. Integration corrections (auto engine/provider selection, adapter request
mapping, length forwarding, regeneration controls, eight-to-four dimension
aggregation, mock length handling) are documented in
`docs/ai-handoff.md` and `docs/ai-review.md`.

### M Doran — Backend Engineer

Owns an independent FastAPI backend baseline and the CRM integration design.

- FastAPI routes and Pydantic contracts for outreach generation/history and lead
  scoring, plus SQLAlchemy models for `outreach_campaigns` and `lead_scores`.
- Provider-neutral CRM payload mapping (`sync_contact`, `update_stage`,
  `activity_log`) and a deterministic sync simulator.
- CRM status/health endpoint and the Milestone 2 backend report.

Team-C keeps its larger canonical backend, because Doran's repository is a smaller
subset with different model names (`lead_id`, `lead_status`, `revenue`). His unique
CRM work was adapted to the canonical `Lead` model in `backend/services/crm.py` and
exposed through `POST /api/v1/crm/sync` (`simulate: true`) and
`GET /api/v1/crm/status` in `backend/routers/analytics.py`. The simulator is always
labelled `mode=simulated`; it never claims a live Salesforce/HubSpot call.

### Sai (Sai Surekha) — Database Engineer

Owns the PostgreSQL database baseline.

- Eight-table relational schema, indexes, constraints and cascade rules.
- Alembic migration scaffold, database-only Docker Compose and the ER diagram.
- SQLAlchemy model modules under `salesgenie-db-workspace/src/database/models/`.

Her workspace remains the deployment baseline in `salesgenie-db-workspace/`. The
canonical schema in `alembic/` and `backend/db.py` already reconciled her table
design and expanded it for authentication and audit columns; the column-by-column
record is in `docs/database-merge-notes.md`.

### Mohamed Isharak M — Team Lead / Backend Integration

Owns the canonical backend and this consolidation.

- Canonical FastAPI backend, JWT/RBAC, Alembic schema, Docker packaging, QA suite and
  the intelligence contract/adapter.
- Consolidation of the four contributions, the AI-by-default switch (`external` engine
  with `auto` provider selection), the scoring dimension fix, the demo seed, the UI
  rewrite integration and the review documentation.

---

## What is original to each repository

| Area | Repository | Integrated location |
|---|---|---|
| Streamlit UI | `Mahek-saba/frontend-infosys` | `frontend/` |
| AI package | `mahidar22/infosys-springboard-internship` / `team-c-mahi` | `ai/`, `utils/` |
| Backend baseline + CRM mapping | `team-c-doran` | canonical backend; CRM parts in `backend/services/crm.py` |
| PostgreSQL schema + migration | `team_c_sai` | `salesgenie-db-workspace/`; reconciled into `alembic/`, `backend/db.py` |
| Canonical backend + integration | `Team-C` | `backend/`, `alembic/`, tests, deployment, docs |

---

## Honest limits

- No real OpenAI or Gemini key exists in this environment. The default demo therefore
  runs the AI agent workflow through the package's deterministic **mock** provider.
  `used_mock=true` and `ai_mode=offline-mock` are exposed by the API and rendered in
  the UI.
- `conversion_probability` remains `null`. No calibrated conversion model was
  contributed, and none is fabricated.
- Email delivery remains `501`. “Record as Sent” records a manual send; it does not
  transmit mail.
- CRM synchronisation is simulated and labelled as such. No live transport exists.
- The work in this working tree is uncommitted. Push it with the original authors
  preserved before presenting the Git history as evidence.
