# Test Cases

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Total cases:** 75
**Verdict key:** `PASS` executed and met · `PARTIAL` executed, requirement partly met ·
`FAIL` executed, requirement not met · `BLOCKED` cannot execute yet ·
`NOT RUN` designed but not executed

`TC-*` identifiers are the ones referenced by [`../SRS.md`](../SRS.md). Automated
references use `file::test_name` and can be run directly with `pytest`.

---

## Module 1 - Prospect management (10 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M1-001 | Create a prospect with valid data returns `201` and normalises e-mail and website | API | FR-001 | `test_api_leads.py::test_create_lead_returns_201_and_normalises_email` | PASS |
| TC-M1-002 | Missing company name, invalid e-mail and over-length fields are rejected with `422` | API | FR-001, AC-005 | `test_api_leads.py::test_create_lead_requires_company_name`, `::test_create_lead_rejects_invalid_email`, `::test_field_length_limits_are_enforced` | PASS |
| TC-M1-003 | Get, list, search and paginate prospects; unknown id returns `404` | API | FR-002 | `test_api_leads.py::test_get_and_list_leads_with_pagination_headers`, `::test_get_missing_lead_returns_404` | PASS |
| TC-M1-004 | Patch updates fields and stage; conflicting e-mail returns `409` | API | FR-003 | `test_api_leads.py::test_patch_lead_updates_fields_and_stage`, `::test_patch_lead_email_conflict_returns_409` | PASS |
| TC-M1-005 | Delete removes the record and requires a manager role | API | FR-004 | `test_api_leads.py::test_delete_requires_manager_role`, UAT-21 | PASS |
| TC-M1-006 | Canonical lifecycle stages accepted, aliases normalised, unknown values rejected | API | FR-005 | `test_api_leads.py::test_create_lead_rejects_invalid_stage`, `::test_stage_aliases_are_accepted`, `::test_unknown_query_stage_is_rejected` | PASS |
| TC-M1-007 | Duplicate e-mail and duplicate company+contact are detected with a `409` and a match reason | API | FR-008 | `test_api_leads.py::test_duplicate_email_returns_409_with_match`, `::test_duplicate_company_and_contact_returns_409`, `::test_duplicate_check_endpoint` | PASS |
| TC-M1-008 | CSV import: happy path, header aliases, in-file duplicates, database duplicates, invalid rows, length violations, unknown stage, non-CSV, empty file, missing company column, non-UTF-8, role check | API | FR-007, FR-008 | `test_api_import.py` (12 tests) | PASS |
| TC-M1-009 | Prospect data survives beyond the current request and connection | Integration | FR-009 | `test_postgres.py::test_orm_round_trip_and_cascade_on_postgres`; UAT-05 read-back | PARTIAL - no process-restart replay (`TC-E2E-002`) |
| TC-M1-010 | Prospect data is retrievable by Modules 2-6 through the API | Integration | FR-010 | UAT-11, UAT-12, UAT-14, UAT-16, UAT-18 all consume the same lead | PASS |

---

## Module 2 - Lead intelligence (7 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M2-001 | Analysis returns business needs, opportunities and industry context | Unit + API | FR-012, FR-013, FR-014 | `test_api_ai.py::test_insights_generate_persist_and_are_evidence_aware` | PASS |
| TC-M2-002 | Qualification information is included and facts are separated from hypotheses | Unit | FR-015 | `test_intelligence.py::test_analysis_separates_facts_from_hypotheses` | PASS |
| TC-M2-003 | Intelligence is stored against the lead and readable afterwards | API | FR-016 | `test_api_ai.py::test_insights_generate_persist_and_are_evidence_aware`, UAT-11 | PASS |
| TC-M2-004 | Intelligence is displayed beside the lead in the UI | UAT | FR-017 | Not executable | NOT RUN - frontend absent |
| TC-M2-005 | Invalid AI output is rejected and not stored | Integration | FR-018, AC-010 | `test_external_adapter.py::test_invalid_package_output_is_rejected` | PASS |
| TC-M2-006 | Provider failure surfaces a clear error without corrupting data | Integration | FR-018, AC-009 | `test_intelligence.py::test_external_backend_fails_loudly_when_package_is_absent`, `test_external_adapter.py::test_package_errors_become_intelligence_errors` | PASS |
| TC-M2-007 | Missing information is reported instead of invented | Unit | FR-012, FR-018 | `test_intelligence.py::test_analysis_reports_missing_information_without_inventing` | PASS |

---

## Module 3 - Outreach (9 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M3-001 | Outreach is generated for a selected lead and persisted as a campaign | API | FR-019, FR-025 | `test_api_ai.py::test_outreach_generation_persists_a_draft`, UAT-12 | PASS |
| TC-M3-002 | All six prompt inputs are accepted; invalid enumerations are rejected | API | FR-020 | `test_api_ai.py::test_outreach_generation_validates_enumerations`, `test_intelligence.py::test_outreach_tone_and_length_change_the_body` | PASS |
| TC-M3-003 | Changing tone, length and outreach type changes the output | Unit | FR-020, AC-012 | `test_intelligence.py::test_outreach_channel_mapping`, `::test_outreach_tone_and_length_change_the_body`, `test_external_adapter.py::test_outreach_request_is_translated_to_the_package_keys` | PASS |
| TC-M3-004 | Refresh produces a new variant | API | FR-021, AC-013 | Not asserted | NOT RUN - coverage gap, no defect |
| TC-M3-005 | A draft can be edited before use | API | FR-022 | `test_api_ai.py::test_outreach_draft_can_be_edited_and_marked_sent`, UAT-12 | PASS |
| TC-M3-006 | Content can be copied to the clipboard | UAT | FR-023 | Not executable | NOT RUN - UI concern |
| TC-M3-007 | Send action is refused visibly and never sends | API | FR-024, AC-015 | `test_api_ai.py::test_outreach_send_never_sends_and_reports_501`, UAT-13 | PASS |
| TC-M3-008 | Campaigns are stored and retrievable per lead | API | FR-025, FR-026 | `test_api_ai.py::test_outreach_generation_persists_a_draft`, UAT-12 | PASS |
| TC-M3-009 | Outreach does not invent industry-specific claims or pain points | Unit | FR-019, AC-011 | `test_intelligence.py::test_outreach_does_not_invent_industry_specific_claims`, `::test_outreach_without_pain_points_declares_the_assumption` | PASS |

---

## Module 4 - Scoring and recommendations (8 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M4-001 | Score is deterministic and bounded to 0-100 | Unit | FR-028 | `test_intelligence.py::test_score_is_bounded_deterministic_and_explainable` | PASS |
| TC-M4-002 | Conversion probability is only produced by a calibrated model | Unit + API | FR-029, AC-016 | `test_intelligence.py::test_heuristic_never_returns_a_calibrated_probability`, `test_api_ai.py::test_scoring_is_explainable_and_never_fakes_probability` | PARTIAL - returns `null` by design; FR-029 blocked by D-09/D-13 |
| TC-M4-003 | All four SRS factors are present and explainable | Unit + UAT | FR-030, AC-017 | `test_intelligence.py::test_score_factor_bounds_are_validated`, UAT-14 | PASS |
| TC-M4-004 | Scores are stored and history is append-only | API | FR-031, AC-018 | `test_api_ai.py::test_scoring_history_is_append_only` | PASS |
| TC-M4-005 | Recommendation includes follow-up timing, channel and content | API + UAT | FR-032, AC-019 | `test_api_ai.py::test_recommendation_endpoint`, UAT-15 | PASS - `suggested_channel` added; BUG-006 closed |
| TC-M4-006 | Missing data produces a defined degraded outcome | Unit | FR-035 | `test_intelligence.py::test_missing_information_lowers_the_score` | PASS |
| TC-M4-007 | Accuracy is measured on an agreed dataset with an agreed metric | UAT | FR-034, AC-020 | Not executable | BLOCKED - SRS D-13 unresolved |
| TC-M4-008 | Scoring requires a write role | API | NFR-005 | `test_api_ai.py::test_scoring_requires_write_role` | PASS |

---

## Module 5 - Conversations and CRM (9 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M5-001 | Meeting/call notes produce a summary | API | FR-036, AC-021 | `test_api_ai.py::test_conversation_summary_persists_interaction`, UAT-16 | PASS |
| TC-M5-002 | Key discussion points are extracted from supplied notes | Unit | FR-037 | `test_intelligence.py::test_conversation_summary_extracts_only_supplied_action_items` | PASS |
| TC-M5-003 | Action items are extracted with evidence | Unit | FR-038 | `test_intelligence.py::test_conversation_summary_extracts_only_supplied_action_items` | PASS |
| TC-M5-004 | Sales interactions are stored and listed | API | FR-039, AC-023 | `test_api_ai.py::test_conversation_summary_persists_interaction`, UAT-16 | PASS |
| TC-M5-005 | Empty or invalid notes produce a clear message | API | FR-036, AC-022 | `test_api_ai.py::test_conversation_requires_content`, `test_intelligence.py::test_conversation_summary_handles_empty_input` | PASS |
| TC-M5-006 | No commitments are invented | Unit | AC-022 | `test_intelligence.py::test_conversation_summary_does_not_invent_commitments` | PASS |
| TC-M5-007 | CRM field mapping is validated | API | FR-040 | `test_api_ai.py::test_crm_mapping_validation` | PASS |
| TC-M5-008 | CRM sync is previewed and real sync fails safely | API | FR-041, FR-042, FR-043 | `test_api_ai.py::test_crm_sync_preview_is_dry_run`, `::test_crm_sync_records_failure_and_retry`, `::test_crm_sync_rejects_unknown_provider` | PASS as specified - live sync BLOCKED by D-06 |
| TC-M5-009 | A failed sync preserves the local interaction and lead record | API + UAT | FR-045, AC-025 | `test_api_ai.py::test_crm_sync_records_failure_and_retry`, UAT-17 | PASS |

---

## Module 6 - Analytics (8 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-M6-001 | Conversion rate is computed and carries a written definition | API | FR-046 | `test_api_ai.py::test_analytics_returns_only_defensible_metrics`, UAT-18 | PASS |
| TC-M6-002 | Pipeline value is withheld while D-10 is open | API | FR-047 | `test_api_ai.py::test_analytics_returns_only_defensible_metrics`, UAT-18 | PASS |
| TC-M6-003 | Average response time is withheld while D-10 is open | API | FR-048 | `test_api_ai.py::test_analytics_returns_only_defensible_metrics`, UAT-18 | PASS |
| TC-M6-004 | Average sales cycle is withheld while D-10 is open | API | FR-049 | `test_api_ai.py::test_analytics_returns_only_defensible_metrics`, UAT-18 | PASS |
| TC-M6-005 | KPI cards render on the dashboard | UAT | FR-050, AC-026 | Not executable | NOT RUN - frontend absent |
| TC-M6-006 | Kanban pipeline matches stored stages | UAT | FR-051, AC-028 | Not executable | NOT RUN - frontend absent; `pipeline_distribution` data is verified |
| TC-M6-007 | Follow-up panel data is derived from stored scores and excludes terminal leads | API | FR-052, AC-029 | `test_api_ai.py::test_follow_ups_are_derived_from_stored_scores`, `::test_terminal_leads_are_excluded_from_follow_ups`, UAT-19 | PASS |
| TC-M6-008 | Analytics interpretation is labelled as observation | API | FR-053 | `test_api_ai.py::test_analytics_insights_are_labelled_observations`, `test_intelligence.py::test_analytics_interpretation_is_observation_only` | PASS |

---

## API and contract (6 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-API-001 | OpenAPI document is served and every documented route is present | API | FR-010 | `test_api_ai.py::test_openapi_spec_is_served` | PASS |
| TC-API-002 | OAuth2 password flow issues a token and `/me` returns the profile | API | NFR-005 | `test_api_auth.py::test_token_issue_and_me`, UAT-02 | PASS |
| TC-API-003 | Errors use `{detail, code, meta}` consistently | API | NFR-003 | Asserted across the API suites (`code` checks in auth, leads, AI) | PASS |
| TC-API-004 | List endpoints return a bare array plus `X-Total-Count`, `X-Page`, `X-Page-Size` | API | FR-002 | `test_api_leads.py::test_get_and_list_leads_with_pagination_headers`, UAT-07 | PASS |
| TC-API-005 | Health endpoint reports database and AI state | API | NFR-011 | `test_api_ai.py::test_health_reports_database_and_ai_state`, UAT-01 | PASS |
| TC-API-006 | Requests without a token are rejected with `401` | API | NFR-005 | `test_api_leads.py::test_unauthenticated_requests_are_rejected`, UAT-04 | PASS |

---

## Database (5 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-DB-001 | The canonical eight tables are declared and created by the migration | DB | FR-009 | `test_schema.py::test_models_declare_the_canonical_eight_tables`, `test_postgres.py::test_migration_created_all_tables` | PASS |
| TC-DB-002 | Migration output matches the ORM metadata | DB | FR-009 | `test_schema.py::test_migration_matches_orm_metadata` | PASS |
| TC-DB-003 | Foreign keys behave as designed and cascade removes dependants | DB | FR-009 | `test_schema.py::test_cascade_delete_removes_dependent_rows`, `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| TC-DB-004 | Uniqueness is enforced and blank e-mails do not collide | DB | FR-008 | `test_schema.py::test_email_key_uniqueness_is_enforced`, `::test_leads_without_email_do_not_collide`, `test_postgres.py::test_unique_email_key_is_enforced_on_postgres` | PASS |
| TC-DB-005 | JSON columns round-trip structured values | DB | FR-016, FR-031 | `test_schema.py::test_json_columns_round_trip`, `test_postgres.py::test_jsonb_columns_accept_structured_values` | PASS |

---

## Security (5 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-SEC-001 | Every business endpoint requires a valid token | API | NFR-005 | `test_api_leads.py::test_unauthenticated_requests_are_rejected`, UAT-04 | PASS |
| TC-SEC-002 | Expired, malformed and wrongly-signed tokens are rejected | Unit + API | NFR-005 | `test_api_auth.py::test_invalid_and_expired_tokens_are_rejected`, `::test_token_signed_with_wrong_secret_is_rejected` | PASS |
| TC-SEC-003 | Passwords are hashed, never stored in clear, and short passwords are refused | Unit | NFR-005 | `test_api_auth.py::test_password_hash_roundtrip_and_rejection`, `::test_short_password_is_refused` | PASS |
| TC-SEC-004 | RBAC: viewer cannot write, non-admin cannot administer users, inactive users cannot log in | API + UAT | NFR-005 | `test_api_leads.py::test_viewer_cannot_create_leads`, `test_api_auth.py::test_admin_can_create_user_and_non_admin_cannot`, `::test_inactive_user_cannot_authenticate`, UAT-20 | PASS |
| TC-SEC-005 | No secrets are committed; only placeholders exist | Manual | NFR-005 | Inspection of `.env.example` and the tracked file list | PASS |

---

## Performance (2 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-PERF-001 | Company analysis completes within 5 seconds | Performance | NFR-001 | Not implemented | NOT RUN - D-11 undefined; UAT timings are not a benchmark |
| TC-PERF-002 | Outreach generation completes within 5 seconds | Performance | NFR-001 | Not implemented | NOT RUN - D-11 undefined |

---

## Deployment (3 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-DEP-001 | The Docker image builds from the Dockerfile | Deployment | NFR-011 | `docker compose build` | PASS - `team-c-api` and `team-c-frontend` built |
| TC-DEP-002 | `docker compose up` starts API and PostgreSQL and health returns ok | Deployment | NFR-011 | `docker compose up -d` | PASS - three services healthy; `/api/v1/health` ok |
| TC-DEP-003 | Dependencies install from scratch into a clean virtual environment | Deployment | NFR-011 | `pip install -r requirements-dev.txt` in a new venv, then full suite | PASS |

---

## End-to-end (3 cases)

| ID | Case | Level | Req | Automated / method | Verdict |
|---|---|---|---|---|---|
| TC-E2E-001 | Full workflow against a live server and real PostgreSQL: create, import, analyse, generate, score, summarise, sync, dashboard, delete | E2E | AC-001 to AC-030 | `scripts/qa_uat.py` - 21 workflows | PASS - 20 passed, 1 partial |
| TC-E2E-002 | Data survives an application restart | E2E | FR-009, AC-001 | Not implemented | NOT RUN |
| TC-E2E-003 | A user completes the workflow through the Streamlit UI | E2E | NFR-003 | Not executable | BLOCKED - frontend absent |

---

## Verdict summary

| Verdict | Count |
|---|---|
| PASS | 60 |
| PARTIAL | 3 |
| BLOCKED | 4 |
| NOT RUN | 8 |
| FAIL | 0 |
| **Total** | **75** |

A `NOT RUN` case is a coverage gap, not a pass. Each is explained in the row above and
carried into [`milestone-test-report.md`](milestone-test-report.md).
