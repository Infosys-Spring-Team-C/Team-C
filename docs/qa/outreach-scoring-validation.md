# Outreach and Scoring Validation Notes (Milestone 2)

**Project:** SalesGenie AI - AI Sales Assistant and Lead Intelligence Platform
**Team:** Team C (Infosys Springboard)
**Date:** 5 November 2026
**Author:** Mohamed Isharak M (QA / Project Lead)
**Scope:** Milestone 2, Modules 3 and 4 - outreach generation, lead scoring,
conversion-probability handling and next-best-action recommendations.
**Build under test:** `main` at `66c1255` plus the 5 November 2026 merge commit,
running in the Docker Compose stack (`db`, `api`, `frontend` all healthy).

---

## 1. How this validation was run

Everything below was executed against the running stack, not inferred from code.

| Step | Command / surface | Result |
|---|---|---|
| Health and engine metadata | `GET /api/v1/health` | `status: ok`, `ai_backend: external`, `ai_provider: mock`, `ai_used_mock: true`, `ai_mode: offline-mock` |
| Seed data | `python -m backend.cli seed-demo --confirm` | 6 clearly-labelled fictional leads across 6 industries |
| Scoring | `POST /api/v1/leads/{id}/scores` for all 6 leads | 6/6 returned a score, factors and an execution block |
| Recommendation | `GET /api/v1/recommendations/{id}` for all 6 leads | 6/6 returned an action, evidence, priority, timing and channel |
| Outreach, primary | `POST /api/v1/outreach/generate` for all 6 leads | 6/6 returned a draft, subject, CTA and execution block |
| Outreach, regenerated | same endpoint with `variant: 1` | 6/6 bodies changed |
| Automated suite | `pytest -q` with `TEST_DATABASE_URL` (PostgreSQL 16) | **176 passed, 0 skipped** |
| Automated suite | `pytest -q` (SQLite) | **170 passed, 6 skipped** (PostgreSQL module self-skips) |

Raw evidence: [`evidence/2026-11-05-milestone2-live-check.json`](evidence/2026-11-05-milestone2-live-check.json).

### Provider state, stated plainly

The `ai.*` package ran through its **deterministic mock provider**. An
`OPENAI_API_KEY` inherited from the host environment was tested first and
rejected by the provider (`HTTP 401`), so no live model output exists for this
build. The engine labels this honestly: `ai_used_mock: true`,
`ai_mode: offline-mock`, and every generated record carries
`execution.used_mock: true`.

---

## 2. Outreach generation across industries

Each lead used `tone=consultative`, `length=short`, `outreach_type=cold_email`,
the lead's own stated need as the goal, its recorded pain points, and a common
call to action.

| Lead | Industry | Score | Subject | Words | Regenerated body differs |
|---|---|---|---|---|---|
| Northwind Logistics | Logistics | 30 | A question about Northwind Logistics's priorities | 34 | Yes |
| Contoso Manufacturing | Manufacturing | 30 | A question about Contoso Manufacturing's priorities | 34 | Yes |
| Fabrikam Retail | Retail | 30 | A question about Fabrikam Retail's priorities | 34 | Yes |
| InnovateAI Labs | Artificial Intelligence | 82 | A question about InnovateAI Labs's priorities | 39 | Yes |
| Bluebird Health | Healthcare AI | 75 | A question about Bluebird Health's priorities | 40 | Yes |
| Vanguard Fintech | Fintech | 75 | A question about Vanguard Fintech's priorities | 42 | Yes |

### What the drafts do

* Address the named contact, not a generic "there".
* Use only the supplied industry, stated need, pain points and call to action.
* State the call to action explicitly and leave the signature as `[Your name]`
  rather than inventing a sender.
* Return `facts_used` and `personalization_rationale` so a reviewer can see what
  the draft is grounded on.

Example (Bluebird Health, after the BUG-017 fix):

```
Hi Sofia,

I'm reaching out to shorten the patient-intake cycle and standardise reporting
across clinics. I saw your team is in Healthcare AI. We help teams explore our
solution. Would a 15-minute conversation next week be useful?

Best,
[Your name]
```

### What the drafts do **not** do

* They do not claim research that was not supplied.
* They do not name a product benefit the record does not support. With an empty
  `product_service` the package writes "our solution" rather than inventing a
  capability.
* They do not send anything. Delivery is a separate endpoint and returns `501`
  because no provider is configured (SRS D-05).

### Prompt and generation changes validated in this pass

| Change | Why | Verified by |
|---|---|---|
| `length` forwarded to the package prompt | It was previously dropped, so the UI control was a no-op | `tests/test_external_adapter.py::test_outreach_request_is_translated_to_the_package_keys` |
| Objective grammar normalised (`"reaching out to ..."`) | Goals written as sentences read incorrectly after "because" | Live drafts for all 6 leads |
| `variant` rotates the regenerated section | "Regenerate variation" must visibly change an offline draft | `test_outreach_variant_rotates_the_regenerated_section`; 6/6 bodies changed live |
| Empty CTA no longer triggers `str.replace("")` | An empty CTA would have inserted text between every character | Code path guard in `ai/agents/outreach.py` |
| Titles skipped when choosing the greeting name | `Dr. Sofia Alvarez` produced `Hi Dr.,` (BUG-017) | `test_outreach_greeting_skips_titles` |

---

## 3. Scoring validation

### 3.1 Observed scores

| Lead | Stage | Score | Band | Fit | Intent | Engagement | Decision readiness |
|---|---|---|---|---|---|---|---|
| Northwind Logistics | discovery | 30 | cold | 62 | 0 | 0 | 9 |
| Contoso Manufacturing | qualified | 30 | cold | 62 | 0 | 0 | 9 |
| Fabrikam Retail | prospecting | 30 | cold | 62 | 0 | 0 | 9 |
| InnovateAI Labs | proposal | 82 | hot | 78 | 96 | 85 | 76 |
| Bluebird Health | negotiation | 75 | hot | 78 | 96 | 35 | 76 |
| Vanguard Fintech | converted | 75 | hot | 78 | 96 | 35 | 76 |

Dimension percentages are the weighted share of the factors the AI package maps
onto each SRS FR-030 dimension. They are derived from the returned factor list,
not stored or invented by the UI.

The three low scores are correct behaviour, not a scoring fault: those records
were seeded in an earlier session with only company, industry, contact and stage.
They carry no engagement history, no stated need and no response behaviour, so
Intent and Engagement score zero and the record is reported as needing
enrichment. The three records seeded with the full field set score 75-82.

### 3.2 Properties that were actually checked

| Property | Method | Result |
|---|---|---|
| Score is bounded 0-100 | unit tests plus live responses | PASS |
| Factor points reconcile to the score | unit tests and API factor lists | PASS |
| Eight AI factors populate the four SRS columns | `dimension_scores()` unit test | PASS (60/70/70/20 fixture) |
| Offline four-factor scores are preserved verbatim | `dimension_scores()` unit test | PASS |
| Same input, same output | repeated live calls and unit tests | PASS |
| Missing context lowers the score | unit test | PASS |
| Negative response behaviour does not inflate intent | unit test | PASS |
| `conversion_probability` is never fabricated | unit test plus live responses (`null`) | PASS |
| Probability band is labelled uncalibrated | API response and UI copy | PASS |

### 3.3 The 85% accuracy target

**The 85% target is not claimed, and no accuracy percentage is reported.**

Why:

1. There is no labelled outcome dataset. Accuracy needs ground-truth conversion
   labels per lead; the repository has fictional demo records and no historical
   outcomes.
2. The shipped scorer is a transparent, configurable heuristic. It is not a
   trained classifier, so "accuracy" would not describe a learned model even if
   labels existed.
3. `conversion_probability` is `null` by design. Any percentage shown next to a
   heuristic score would be read as a calibrated probability, which the project
   rules forbid.

What can be said honestly: on the six seeded demo records the score ordering is
consistent with the recorded lifecycle stage (proposal/negotiation/converted
above prospecting/discovery). That is a **sanity check on a constructed demo
set, not a validation result**: the score consumes sales stage as an input, so
the agreement is partly circular and the sample is far too small.

Closing the 85% item requires a labelled dataset and a calibration split. The
work to do that is recorded as a limitation, not as a pass.

---

## 4. Recommendation engine

For each lead the engine returned an action, a reason, supporting evidence with
a source and confidence, a priority, a suggested timing and a channel.

* InnovateAI Labs (proposal, two demos, proposal sent):
  * priority **High**, timing **Within one business day**, channel **email**
  * action: "Send a tailored recap and request a discovery meeting."
  * evidence: the recorded engagement history and stated need, both sourced to
    the lead record.
* Leads with no recorded interaction or stated need received no channel and an
  enrichment-first action, rather than a fabricated follow-up.

The recommendation is generated by the same engine boundary as scoring and
carries its own `execution` block, so its provider and `used_mock` state are
visible per record.

---

## 5. Frontend checks (Outreach Studio)

Verified in the browser against the containerised stack:

| Control | Behaviour observed |
|---|---|
| Lead selector | Lists the seeded prospects with company and stage |
| Tone / length / channel / goal / CTA / pain points | Sent to the API; the draft reflects tone and length |
| Generate draft | Creates and stores an `Outreach_Campaigns` row |
| Regenerate variation | Increments `variant`; the body changes and a new row is stored |
| Edit subject and body | Editable fields; the edited text is what is saved |
| Copy message | Copies the current subject and body |
| Save draft | Persists the edited draft; the stored body was read back through the API after saving |
| Record as sent | Marks the draft sent manually; no email is transmitted |
| Send email | Refuses visibly with the backend's `501` reason |
| Lead Score card | Shows score, band, `n/a` conversion probability and the four dimension bars from the stored factors |
| Outreach Strategy card | Shows priority, timing, channel and content strategy from the recommendation |

The final browser pass generated draft #30, edited it, saved it, confirmed the saved
body through `GET /api/v1/leads/6/outreach-drafts`, recorded a draft as sent and observed
the `501` dispatch refusal. The Lead Score card rendered `75/100`, band `Qualified`,
`n/a` for conversion probability and dimension bars Fit 70, Intent 85, Engagement 35,
Decision readiness 35. The Outreach Strategy card rendered priority `High`, timing
`Within one business day`, channel `email` and the suggested content.

No console errors were observed on the Outreach Studio page. Screenshots are not
included because the browser tooling in this environment exposes the DOM and
computed styles but cannot capture images.

---

## 6. Defects found and fixed during this validation

| ID | Defect | Fix |
|---|---|---|
| BUG-017 | `Hi Dr.,` greeting for titled contacts | Honorific-aware first-name helper in the AI package and the heuristic engine |
| BUG-018 | A keyed provider without its SDK made the engine unavailable | `auto` now falls back to the labelled mock provider; explicit providers still fail loudly |

Both are closed with tests and are recorded in [`bug-log.md`](bug-log.md).

---

## 7. Limitations

1. No live OpenAI or Gemini call succeeded. The key available in this
   environment returned `HTTP 401`; the mock provider was used and labelled.
2. No scoring accuracy figure exists, for the reasons in section 3.3.
3. Outreach quality was judged against grounding rules (no invented facts, no
   fabricated research), not by human sales reviewers.
4. Only six demo leads across six industries were exercised. Broader industry
   coverage needs more records and a review panel.
5. Email delivery and CRM transport remain unimplemented by design (SRS D-05,
   D-06); the CRM path now has a clearly-labelled simulator.

---

## 8. Verdict

**Outreach generation and the Outreach Studio: PASS for demonstration.**
Generation honours channel, tone, length, goal, pain points and industry,
regeneration changes the draft, edits persist, and delivery is refused honestly.

**Lead scoring and recommendations: PASS for demonstration, with the accuracy
target explicitly unmeasured.** Scores are bounded, explainable, deterministic
and mapped onto the four SRS dimensions; conversion probability is withheld
rather than invented.

**Not signed off:** the 85% accuracy target and human usability acceptance.
