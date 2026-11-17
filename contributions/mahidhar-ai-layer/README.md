# DealFlow AI — AI/ML Layer

The intelligence layer of the AI Sales Intelligence Platform: **lead scoring**,
**next-best-action recommendations** and **conversation summarisation**.

Pure Python. No web framework, no UI, no database required to run. Each service is a
function you can call from anywhere — a FastAPI route, a worker, a notebook, a batch job.

```python
from sales_intel.ai.scoring.engine import score_lead
from sales_intel.ai.nba.engine import recommend
from sales_intel.ai.summarization.engine import summarise
```

| Deliverable | Day | Module | Entry point |
|---|---|---|---|
| Tuned prompts + scoring weights | 14 | M2/M4 | `scripts/tune_weights.py`, `scripts/tune_prompts.py` |
| Next-best-action engine | 15 | M4 | `sales_intel/ai/nba/engine.py` |
| Conversation summarisation | 24 | M5 | `sales_intel/ai/summarization/engine.py` |

---

## Quick start

```bash
pip install -r requirements.txt     # pydantic + httpx + pytest
make demo                           # run all three services in the terminal
make test                           # 86 tests
```

```bash
make data      # sample dataset (320 labelled leads)
make tune      # Day 14: tune weights → data/artifacts/ + report
make prompts   # Day 14: compare prompt variants (offline)
```

## The three services

### 1. Lead scoring — `ai/scoring/engine.py`

```
raw signals → 4 dimension subscores (0-100) → weighted composite → P(conversion)
```

```python
from sales_intel.ai.scoring.engine import score_lead
from sales_intel.schemas import LeadFeatures

lead = LeadFeatures(lead_id="L1", email_opens=14, pricing_page_visits=7,
                    budget_confirmed=1, timeline_months=3, ...)
result = score_lead(lead)
result.score                  # 77.08
result.band                   # 'Hot'
result.conversion_probability # 0.8519
result.drivers                # per-dimension point attribution
```

Every point is attributable to one dimension — that is what makes the Milestone-2
accuracy claim auditable.

### 2. Next best action — `ai/nba/engine.py`

```python
from sales_intel.ai.nba.engine import recommend
from sales_intel.schemas import LeadContext

nba = recommend(lead, LeadContext(lead_id="L1", lifecycle_stage="qualified", ...))
nba.priority            # P0..P3
nba.next_touch_date     # next business day, never Sunday
nba.cadence             # 4-step multi-channel sequence
nba.channel_mix         # shares sum to 100%
nba.content             # type, angle, asset, CTA, tone, key messages
nba.rationale           # why — string per decision
nba.suppress            # True when guardrails fire (DNC, frequency cap)
```

Timing, priority and channel choice are deterministic rules; the LLM only writes copy.
Guardrails: do-not-contact, per-priority contact-frequency caps, quiet hours, staleness decay.

### 3. Conversation summarisation — `ai/summarization/engine.py`

```python
from sales_intel.ai.summarization.engine import summarise, to_interaction_record

summary = summarise(utterances, interaction_id="INT-1", lead_id="L1")
summary.summary                  # executive digest, not transcript soup
summary.key_discussion_points    # topic + sentiment + quote
summary.action_items             # task, owner, owner_side, due_date, priority, quote
summary.objections               # gated on negative sentiment
summary.competitors_mentioned
to_interaction_record(summary)   # 18-field Sales_Interactions payload
```

Handles relative dates (`"by Friday"`, `"in two weeks"`, `"12/11"`), owner attribution
(`"I'll send"` → speaker, `"please send"` → the other party) and infers which speakers
are internal when no metadata is supplied.

**Runs with no API key.** Set `OPENAI_API_KEY` to route through an LLM; if the provider
fails, returns malformed JSON or returns nothing usable, the heuristic engine takes over
so a CRM record is never blanked.

---

## Day 14 — tuning the model

```bash
python scripts/tune_weights.py --seed 42
```

| | accuracy | AUC |
|---|---|---|
| default weights | 84.38% | 0.9364 |
| **tuned (shipped)** | **89.06%** | **0.9401** |

5-fold stratified CV through the same code path as production. Weights live on the
simplex (non-negative, sum = 1.0) so scores stay comparable across versions. Seeded and
reproducible. The generator prints the **oracle ceiling** for the dataset so a target that
cannot be met is reported as such instead of quietly claimed.

`python scripts/tune_prompts.py` scores every prompt variant against structural
guardrails and ships `v2` for both outreach and summarisation.

## Optional infrastructure

| Need | How |
|---|---|
| Postgres persistence | `export SI_DATABASE_URL=postgresql://…` — DDL for `sales_interactions`, `action_items`, `lead_scores`, `nba_recommendations` is in `db/repository.py` |
| Different LLM provider | override `base_url` / `model` in `ai/llm/client.py` |
| Nothing | defaults to in-memory repository + heuristic engine |

## Layout

```
sales_intel/
  config.py                  tunable knobs (feature caps, weights, NBA rules, summary settings)
  schemas.py                 pydantic contracts
  utils.py                   utcnow()
  ai/scoring/engine.py       subscores, composite score, probability, drivers
  ai/scoring/tuner.py        CV, ROC-AUC, Dirichlet search, artifact writer
  ai/nba/engine.py           priority, timing, channel mix, content, guardrails
  ai/summarization/engine.py summarisation, date/owner parsing, CRM record shape
  ai/prompts/registry.py     versioned prompt templates (v1/v2/v3)
  ai/llm/client.py           provider shim: retries, JSON mode, timing, degradation
  ai/agents/lead_agent.py    load → score → summarise → NBA → outreach pipeline
  db/repository.py           in-memory + PostgreSQL persistence for AI outputs
scripts/
  run_ai_demo.py             headless demo of all three services
  generate_sample_data.py    synthetic leads with a documented latent-truth model
  tune_weights.py            Day 14 (weights) → data/artifacts/
  tune_prompts.py            Day 14 (prompts)
  make_milestone3_report.py  regenerates the Milestone-3 test report (.docx)
tests/                       86 tests
data/artifacts/              tuned weights + tuning reports (committed evidence)
```

## Tests

```
tests/test_scoring.py         subscores, bands, drivers, config validation
tests/test_tuner.py           AUC/accuracy correctness, fold balance, learning, artifacts
tests/test_nba.py             timing, priorities, guardrails, persona/stage content
tests/test_summarization.py   date parsing, topics, owners, LLM failure modes
tests/test_agents.py          graph order, conditional routing, loop protection
```

## Known limits

- Scoring is a transparent weighted model, not gradient-boosted — deliberate, so the
  ≥85% target is met *and* every point is explainable.
- Heuristic summaries cap their own confidence at 0.85 so they cannot masquerade as
  LLM-grade output.
- No web layer in this package: wire these functions into your own API if you need one.
