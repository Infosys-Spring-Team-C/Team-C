# AI Quality Validation

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Engine under test:** `HeuristicEngine` (default, offline, deterministic)
**Adapter under test:** `ExternalAIEngine` against a stub package

The SRS leaves the accuracy metric and dataset open (Decision D-13), so this document does
**not** report an accuracy percentage. It validates the properties that can be checked
without a labelled dataset: correctness of structure, determinism, boundary behaviour,
refusal to fabricate, and contract conformance.

---

## 1. What "good AI output" means here

An output passes only if all seven hold:

| # | Property | Why it matters |
|---|---|---|
| 1 | **Well-formed** - matches the typed contract | A malformed output must never reach the database |
| 2 | **Grounded** - every claim traces to supplied data | Prevents invented company facts |
| 3 | **Honest about gaps** - `missing_information` populated | The user must know what the system does not know |
| 4 | **Deterministic** - same input, same output | Makes the behaviour testable and reproducible |
| 5 | **Bounded** - scores 0-100, weights fixed | Keeps the scale meaningful |
| 6 | **Non-fabricating about the model** - no fake probability | An uncalibrated heuristic must not present itself as a trained model |
| 7 | **Actionable** - the recommendation can be acted on | Otherwise the output is decoration |

---

## 2. Determinism

**Test:** run the same analysis, scoring, outreach and summary twice and compare.

| Output | Deterministic | Test |
|---|---|---|
| Company analysis | Yes | `test_intelligence.py::test_score_is_bounded_deterministic_and_explainable` (scoring), repeated runs in `test_api_ai.py` |
| Lead score | Yes - identical factors, points and score | Same |
| Outreach draft | Yes for identical inputs | `test_outreach_tone_and_length_change_the_body` asserts change *only* when an input changes |
| Conversation summary | Yes | `test_conversation_summary_extracts_only_supplied_action_items` |

Determinism is a property of the heuristic engine. An LLM-backed engine would not be
deterministic; that is why the engine is behind a contract and reports its
`provider`/`model` in every `execution` block.

---

## 3. Grounding and non-fabrication

| Check | Method | Result |
|---|---|---|
| Analysis separates supplied facts from hypotheses | Inspect `supported_facts` (source-typed) versus inferred items | PASS - `test_analysis_separates_facts_from_hypotheses` |
| Missing context is declared | A sparse lead must populate `missing_information` | PASS - `test_analysis_reports_missing_information_without_inventing` |
| Outreach does not invent industry claims | A lead with no industry must not produce industry-specific assertions | PASS - `test_outreach_does_not_invent_industry_specific_claims` |
| Outreach declares assumptions | A lead with no pain points must say so | PASS - `test_outreach_without_pain_points_declares_the_assumption` |
| Summaries do not invent commitments | Notes with no commitment must produce no `action_items` entry | PASS - `test_conversation_summary_does_not_invent_commitments` |
| Action items are traceable | Each item carries the evidence it came from | PASS - `test_conversation_summary_extracts_only_supplied_action_items` |
| Analytics interpretation is an observation, not a fact | Output must be labelled | PASS - `test_analytics_interpretation_is_observation_only` |
| Analytics interpretation with no data is honest | Must not describe a trend that does not exist | PASS - `test_analytics_interpretation_without_data_is_honest` |

Every AI response also carries a `disclaimer` stating that no external research was
performed.

---

## 4. Boundary and adversarial inputs

| # | Input | Expected | Result |
|---|---|---|---|
| A-01 | Empty company name | Rejected at validation, never scored | PASS - `422` |
| A-02 | Lead with only a company name | Low score plus `missing_information`, no exception | PASS - `test_missing_information_lowers_the_score` |
| A-03 | Negative response behaviour ("not interested", "no budget") | Must not inflate intent | PASS - `test_negative_response_behaviour_does_not_inflate_intent` |
| A-04 | Empty transcript and empty notes | Rejected with a clear message | PASS - `test_conversation_requires_content` |
| A-05 | Empty string transcript directly to the engine | Honest empty summary, no invention | PASS - `test_conversation_summary_handles_empty_input` |
| A-06 | More than 10 pain points | Rejected with `422` | PASS - request validator |
| A-07 | Unknown outreach type or tone | Rejected with `422` | PASS - `test_outreach_generation_validates_enumerations` |
| A-08 | Unknown lead id | `404`, nothing written | PASS - `test_insights_unknown_lead_returns_404` |
| A-09 | Malformed package output (external engine) | `IntelligenceError`, API `502`, nothing stored | PASS - `test_invalid_package_output_is_rejected` |
| A-10 | Package raises during a call | Translated to `IntelligenceError` | PASS - `test_package_errors_become_intelligence_errors` |
| A-11 | `SALES_GENIE_AI_BACKEND=external` with no package | Loud failure at construction, health reports `ai_status: unavailable` | PASS - `test_external_backend_fails_loudly_when_package_is_absent` |
| A-12 | Unsupported backend name | Configuration error, not a silent fallback | PASS - `test_unsupported_backend_is_a_configuration_error` |
| A-13 | Factor weights altered out of range | Validation rejects the factor | PASS - `test_score_factor_bounds_are_validated` |

---

## 5. Output contract conformance

| Operation | Required shape | Verified |
|---|---|---|
| `analyze_lead` | overview, supported facts, needs, opportunities, challenges, industry context, discovery questions, missing information, qualification, disclaimer | Yes |
| `generate_outreach` | channel, subject, body, call to action, rationale, facts used, assumptions, missing context | Yes |
| `score_lead` | 0-100 score, category, four factors, signals, missing information, next action, band, note | Yes |
| `summarize_conversation` | executive summary, discussion points, requirements, pain points, objections, buying signals, action items, follow-up, source note | Yes |
| `recommend` | related lead, action, reason, evidence, priority, timing, follow-up draft | Yes, except an explicit channel field - **BUG-006** |
| `interpret_analytics` | observations only, with a caveat | Yes |

---

## 6. The conversion-probability decision

`FR-029` asks for a conversion-probability estimate. The shipped engine returns:

```json
{
  "score": 56,
  "conversion_probability": null,
  "probability_band": "medium",
  "probability_note": "No calibrated conversion model is configured. The band is an uncalibrated heuristic ..."
}
```

**Why this is the correct result for this milestone**

* No labelled dataset exists (SRS D-13), so no model can be calibrated.
* A number such as `0.73` produced by summing heuristic points would look calibrated and
  would be quoted as if it were. That is a data-integrity defect, not a feature.
* The band and the note give the user a usable signal while making the limitation explicit.
* When a calibrated model is configured, the field is populated and the note changes.

**Test:** `test_heuristic_never_returns_a_calibrated_probability` and
`test_scoring_is_explainable_and_never_fakes_probability`.

**Verdict:** FR-029 is `PARTIAL` by design. This is a deliberate, documented limitation,
not an oversight.

---

## 7. What cannot be validated yet

| Property | Blocker |
|---|---|
| Accuracy against a labelled dataset (target >= 85%) | SRS D-13: no metric, no dataset |
| Consistency across providers | SRS D-01: provider not selected; only the heuristic and a stub were exercised |
| Latency against the 5-second target | SRS D-11: measurement conditions undefined |
| Real-world output quality on live prospect data | No production data is used in testing |
| Behaviour of the real `ai.*` package | Package absent from the repository - **BUG-008** |

None of these is reported as passing.

---

## 8. Summary

| Area | Verdict |
|---|---|
| Structure and contract conformance | PASS |
| Determinism | PASS |
| Grounding and non-fabrication | PASS |
| Boundary and adversarial inputs | PASS (13 of 13) |
| Adapter error translation | PASS |
| Calibrated probability | PARTIAL by design |
| Recommendation channel field | PARTIAL - BUG-006 |
| Accuracy metric | BLOCKED - D-13 |
| Real package integration | BLOCKED - BUG-008 |

The AI layer is safe to demonstrate: it produces structured, reproducible, clearly-labelled
output and refuses to invent what it does not know. It is not yet proven accurate, because
no one has defined what accurate means for this project.
