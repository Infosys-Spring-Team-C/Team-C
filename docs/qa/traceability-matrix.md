# Requirements Traceability Matrix

**Date:** 27 October 2026
**Author:** Mohamed Isharak M
**Source of requirements:** [`../SRS.md`](../SRS.md) - functional requirements `FR-001` to
`FR-053` and acceptance criteria `AC-001` to `AC-030`

**Verdict key:** `PASS` verified · `PARTIAL` partly verified · `BLOCKED` cannot verify yet ·
`NOT RUN` not executed · `FAIL` not met

---

## 1. Summary

| Verdict | Functional requirements (53) | Acceptance criteria (30) |
|---|---|---|
| PASS | 35 | 19 |
| PARTIAL | 5 | 7 |
| BLOCKED | 12 | 4 |
| NOT RUN | 1 | 0 |
| FAIL | 0 | 0 |

The frontend was scored before it was merged. It now exists, the adapter passes 12/12 live
checks, and the scoring screen was exercised in a browser. Only the requirements that were
directly observed end to end have moved to `PASS` (`FR-032`, `FR-033`, `AC-019`). Rows whose
note still says "no UI" are **awaiting human acceptance**, not missing: the remaining
`BLOCKED` rows are the CRM transport (SRS D-06), the undefined accuracy dataset (SRS D-13),
or UI interactions that no one has clicked through yet. None is a hidden failure.

---

## 2. Functional requirements

| FR | Requirement (abridged) | Module | Test case(s) | Evidence | Verdict |
|---|---|---|---|---|---|
| FR-001 | Create a prospect | M1 | TC-M1-001, TC-M1-002 | `test_create_lead_returns_201_and_normalises_email`, UAT-05 | PASS |
| FR-002 | View prospect list and detail | M1 | TC-M1-003 | `test_get_and_list_leads_with_pagination_headers`, UAT-07 | PASS |
| FR-003 | Update a prospect | M1 | TC-M1-004 | `test_patch_lead_updates_fields_and_stage`, UAT-08 | PASS |
| FR-004 | Delete a prospect | M1 | TC-M1-005 | `test_delete_requires_manager_role`, UAT-21 | PASS |
| FR-005 | Lifecycle stages and stage movement | M1 | TC-M1-006 | `test_stage_aliases_are_accepted`, UAT-08 | PASS |
| FR-006 | Add a lead manually through the Leads UI | M1 | TC-M1-001 | API path verified; no UI | BLOCKED |
| FR-007 | Import leads from CSV | M1 | TC-M1-008 | `test_api_import.py` (12 tests), UAT-09 | PASS |
| FR-008 | Detect and report duplicate leads | M1 | TC-M1-007, TC-M1-008 | `test_duplicate_email_returns_409_with_match`, UAT-06 | PASS |
| FR-009 | Persist prospect data across sessions | M1 | TC-M1-009 | `test_orm_round_trip_and_cascade_on_postgres`; restart replay not run | PARTIAL |
| FR-010 | Prospect data retrievable by Modules 2-6 | M1 | TC-M1-010 | Every UAT workflow consumes the same stored lead | PASS |
| FR-011 | Accept a company profile for analysis | M2 | TC-M2-001 | `test_insights_generate_persist_and_are_evidence_aware` | PASS |
| FR-012 | Produce business-needs analysis | M2 | TC-M2-001, TC-M2-007 | `test_analysis_reports_missing_information_without_inventing` | PASS |
| FR-013 | Produce business opportunities | M2 | TC-M2-001 | `test_insights_generate_persist_and_are_evidence_aware` | PASS |
| FR-014 | Produce industry insights | M2 | TC-M2-001 | Same test; `industry_context` populated | PASS |
| FR-015 | Produce lead qualification information | M2 | TC-M2-002 | `test_analysis_separates_facts_from_hypotheses` | PASS |
| FR-016 | Store intelligence against the lead | M2 | TC-M2-003, TC-DB-005 | `test_insights_generate_persist_and_are_evidence_aware`, UAT-11 | PASS |
| FR-017 | Display intelligence beside the lead in the UI | M2 | TC-M2-004 | API returns it; no UI | BLOCKED |
| FR-018 | Validate AI output and handle provider failure | M2 | TC-M2-005, TC-M2-006 | `test_invalid_package_output_is_rejected`, `test_package_errors_become_intelligence_errors` | PASS |
| FR-019 | Generate personalised outreach | M3 | TC-M3-001, TC-M3-009 | `test_outreach_generation_persists_a_draft`, UAT-12 | PASS |
| FR-020 | Accept the six prompt inputs | M3 | TC-M3-002, TC-M3-003 | `test_outreach_tone_and_length_change_the_body`, `test_outreach_channel_mapping` | PASS |
| FR-021 | Refresh/regenerate for a new variant | M3 | TC-M3-004 | No test asserts a differing variant | NOT RUN |
| FR-022 | Edit a generated outreach | M3 | TC-M3-005 | `test_outreach_draft_can_be_edited_and_marked_sent`, UAT-12 | PASS |
| FR-023 | Copy outreach to the clipboard | M3 | TC-M3-006 | UI concern; no UI | BLOCKED |
| FR-024 | Provide a send action | M3 | TC-M3-007 | `test_outreach_send_never_sends_and_reports_501`, UAT-13 | PASS (per AC-015) |
| FR-025 | Store outreach campaigns | M3 | TC-M3-001, TC-M3-008 | `test_outreach_generation_persists_a_draft` | PASS |
| FR-026 | Retrieve outreach history | M3 | TC-M3-008 | UAT-12 history read-back | PASS |
| FR-027 | Outreach UI exposes generate/refresh/edit/copy/send | M3 | TC-M3-006 | No UI | BLOCKED |
| FR-028 | Produce a lead score | M4 | TC-M4-001 | `test_score_is_bounded_deterministic_and_explainable` | PASS |
| FR-029 | Produce a conversion-probability estimate | M4 | TC-M4-002 | `test_heuristic_never_returns_a_calibrated_probability` - returns `null` | PARTIAL |
| FR-030 | Score on engagement, fit, intent, decision readiness | M4 | TC-M4-003 | `test_score_factor_bounds_are_validated`, UAT-14 | PASS |
| FR-031 | Store scores with history | M4 | TC-M4-004 | `test_scoring_history_is_append_only` | PASS |
| FR-032 | Recommendation with timing, channel and content | M4 | TC-M4-005 | `test_recommendation_endpoint` - `suggested_channel` present; BUG-006 closed | PASS |
| FR-033 | Display score and recommendation in the UI | M4 | TC-M4-003, TC-M4-005 | Browser check: score 20/100 and recommended action rendered; AppTest 0 exceptions | PASS |
| FR-034 | Accuracy validation against an agreed dataset | M4 | TC-M4-007 | SRS D-13 unresolved | BLOCKED |
| FR-035 | Degraded outcome on missing data | M4 | TC-M4-006 | `test_missing_information_lowers_the_score` | PASS |
| FR-036 | Summarise meeting/call notes | M5 | TC-M5-001, TC-M5-005 | `test_conversation_summary_persists_interaction`, UAT-16 | PASS |
| FR-037 | Extract key discussion points | M5 | TC-M5-002 | `test_conversation_summary_extracts_only_supplied_action_items` | PASS |
| FR-038 | Extract action items | M5 | TC-M5-003 | Same test; `action_items` asserted | PASS |
| FR-039 | Store sales interactions | M5 | TC-M5-004 | `test_conversation_summary_persists_interaction`, UAT-16 | PASS |
| FR-040 | CRM field mapping | M5 | TC-M5-007 | `test_crm_mapping_validation` | PASS (validation only) |
| FR-041 | Sync contacts and activities to the CRM | M5 | TC-M5-008 | Transport not configured, SRS D-06 | BLOCKED |
| FR-042 | Sync deal stage to the CRM | M5 | TC-M5-008 | Transport not configured, SRS D-06 | BLOCKED |
| FR-043 | Record CRM sync logs | M5 | TC-M5-008 | `test_crm_sync_records_failure_and_retry`, UAT-17 | PASS |
| FR-044 | Conversations UI | M5 | TC-M5-001 | No UI | BLOCKED |
| FR-045 | Handle CRM failure without losing the local record | M5 | TC-M5-009 | `test_crm_sync_records_failure_and_retry`, UAT-17 | PASS |
| FR-046 | Display conversion rate | M6 | TC-M6-001 | `test_analytics_returns_only_defensible_metrics`, UAT-18 | PASS |
| FR-047 | Display pipeline value | M6 | TC-M6-002 | `null` + `pending_definition` while D-10 is open | PARTIAL |
| FR-048 | Display average response time | M6 | TC-M6-003 | `null` + `pending_definition` while D-10 is open | PARTIAL |
| FR-049 | Display average sales cycle | M6 | TC-M6-004 | `null` + `pending_definition` while D-10 is open | PARTIAL |
| FR-050 | KPI cards | M6 | TC-M6-005 | No UI | BLOCKED |
| FR-051 | Kanban pipeline visualisation | M6 | TC-M6-006 | No UI; `pipeline_distribution` data verified | BLOCKED |
| FR-052 | Follow-up recommendations panel | M6 | TC-M6-007 | Data verified; panel not rendered | BLOCKED |
| FR-053 | Dashboard renders on an empty dataset, consistent with the database | M6 | TC-M6-007 | API empty-dataset verified; rendering not | BLOCKED |

---

## 3. Acceptance criteria

| AC | Criterion (abridged) | Test case(s) | Verdict |
|---|---|---|---|
| AC-001 | Create a prospect and find it again after an application restart | TC-M1-001, TC-E2E-002 | PARTIAL - persistence across requests proven, restart not replayed |
| AC-002 | Update and delete; deleted records disappear | TC-M1-004, TC-M1-005 | PASS |
| AC-003 | Valid CSV imports; duplicates reported, not stored twice | TC-M1-008 | PASS |
| AC-004 | Stages assignable and visible per lead | TC-M1-006 | PASS |
| AC-005 | Invalid input gives a clear error and no corrupt record | TC-M1-002, TC-M1-008 | PASS |
| AC-006 | Structured needs, opportunities and industry insights | TC-M2-001 | PASS |
| AC-007 | Intelligence stored and displayed beside the lead after reload | TC-M2-003, TC-M2-004 | PARTIAL - stored and readable; display blocked |
| AC-008 | Qualification included in the intelligence output | TC-M2-002 | PASS |
| AC-009 | Provider unavailable gives a clear error, data intact | TC-M2-006 | PASS |
| AC-010 | Output failing validation is rejected, not stored | TC-M2-005 | PASS |
| AC-011 | Outreach generated from the six inputs | TC-M3-001, TC-M3-002 | PASS |
| AC-012 | Changing inputs changes the output | TC-M3-003 | PASS |
| AC-013 | Refresh yields a new variant; edit and copy work | TC-M3-004, TC-M3-005, TC-M3-006 | PARTIAL - edit verified; refresh not asserted; copy blocked |
| AC-014 | Campaigns stored and retrievable per lead | TC-M3-008 | PASS |
| AC-015 | Send works or is visibly marked unavailable | TC-M3-007 | PASS |
| AC-016 | Score and probability produced within the agreed scale | TC-M4-001, TC-M4-002 | PARTIAL - score yes, probability withheld |
| AC-017 | All four factors considered | TC-M4-003 | PASS |
| AC-018 | Scores stored and retrievable | TC-M4-004 | PASS |
| AC-019 | Recommendations include timing, channel and content | TC-M4-005 | PASS - `suggested_channel` added; BUG-006 closed |
| AC-020 | Scoring accuracy meets the agreed target | TC-M4-007 | BLOCKED - D-13 |
| AC-021 | Notes produce summary, points and actions | TC-M5-001, TC-M5-002, TC-M5-003 | PASS |
| AC-022 | Empty/invalid notes give a clear message, no fabrication | TC-M5-005, TC-M5-006 | PASS |
| AC-023 | Interactions stored and listed in the Conversations UI | TC-M5-004 | PARTIAL - stored and listed via API; UI blocked |
| AC-024 | Sync attempts, successes and failures logged | TC-M5-008 | PASS |
| AC-025 | Failed sync does not delete or corrupt the local record | TC-M5-009 | PASS |
| AC-026 | All four KPIs render with agreed definitions | TC-M6-001 to TC-M6-005 | BLOCKED - D-10 and no UI |
| AC-027 | KPI values match manual computation | TC-M6-001 | PARTIAL - conversion rate only; manual cross-check not performed |
| AC-028 | Kanban matches M1 stage data | TC-M6-006 | BLOCKED - no UI |
| AC-029 | Follow-up panel shows M4-derived recommendations | TC-M6-007 | PARTIAL - data verified, panel not rendered |
| AC-030 | Dashboard renders with an empty database | TC-M6-007 | BLOCKED - no UI; API empty case verified |

---

## 4. Coverage by module

| Module | FRs | PASS | PARTIAL | BLOCKED | NOT RUN |
|---|---|---|---|---|---|
| M1 Prospect management | 10 | 8 | 1 | 1 | 0 |
| M2 Lead intelligence | 8 | 7 | 0 | 1 | 0 |
| M3 Outreach | 9 | 6 | 0 | 2 | 1 |
| M4 Scoring | 8 | 4 | 2 | 2 | 0 |
| M5 Conversations and CRM | 10 | 7 | 0 | 3 | 0 |
| M6 Analytics | 8 | 1 | 3 | 4 | 0 |
| **Total** | **53** | **33** | **6** | **13** | **1** |

M6 shows the lowest pass rate because four of its eight requirements are dashboard
rendering, and the dashboard does not exist yet. The data behind every M6 widget is
verified.
