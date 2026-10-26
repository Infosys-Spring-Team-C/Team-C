# API Test Matrix

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Base URL:** `http://127.0.0.1:8000` (local) or `http://127.0.0.1:8011` (UAT run)
**Contract reference:** [`../api-contract.md`](../api-contract.md)
**Machine-readable:** `/openapi.json`, browsable at `/docs`

All endpoints are under `/api/v1` unless stated. Every endpoint except the token issue and
the health/root routes requires `Authorization: Bearer <token>`.

**Role key:** `public` = no token · `any` = any authenticated role ·
`writer` = admin, manager or rep · `manager` = admin or manager · `admin` = admin only.

---

## 1. Authentication

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/auth/token` | public | `200` token + `expires_in` | `401 invalid_credentials` for wrong password **and** unknown user (same response); `400 auth_disabled` when disabled | `test_token_issue_and_me`, `test_wrong_password_and_unknown_user_both_return_401` |
| GET | `/auth/me` | any | `200` user profile | `401` without/with invalid token | `test_token_issue_and_me`, `test_invalid_and_expired_tokens_are_rejected` |
| GET | `/auth/users` | admin | `200` user list | `401`, `403` for non-admin | `test_admin_can_create_user_and_non_admin_cannot` |
| POST | `/auth/users` | admin | `201` user | `409 user_exists`, `422 invalid_role`, `403` for non-admin | `test_admin_can_create_user_and_non_admin_cannot`, `test_new_user_can_authenticate` |
| PATCH | `/auth/users/{user_id}` | admin | `200` updated user | `404 user_not_found`, `422 invalid_role` | `test_admin_can_deactivate_and_change_role` |

---

## 2. Prospects (Module 1)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/leads` | writer | `201` lead | `409 duplicate_lead` with `meta.match`, `422` validation (missing company, bad e-mail, over-length) | `test_create_lead_returns_201_and_normalises_email`, `test_create_lead_requires_company_name`, `test_duplicate_email_returns_409_with_match` |
| GET | `/leads` | any | `200` bare array + `X-Total-Count`, `X-Page`, `X-Page-Size` | `422` for an unknown `stage` | `test_get_and_list_leads_with_pagination_headers`, `test_unknown_query_stage_is_rejected` |
| GET | `/leads/{lead_id}` | any | `200` lead | `404 lead_not_found` | `test_get_missing_lead_returns_404` |
| PATCH | `/leads/{lead_id}` | writer | `200` updated lead | `404`, `409` on e-mail conflict, `422` | `test_patch_lead_updates_fields_and_stage`, `test_patch_lead_email_conflict_returns_409` |
| DELETE | `/leads/{lead_id}` | manager | `204` no body | `403` for rep/viewer, `404` | `test_delete_requires_manager_role` |
| POST | `/leads/duplicate-check` | any | `200 {is_duplicate, matched_lead_id, match_reason}` | — | `test_duplicate_check_endpoint` |
| POST | `/leads/import` | writer | `200` import report (`imported`, `duplicates`, `invalid`, `total_rows`, `errors`, `duplicate_rows`) | `400` non-CSV / empty / non-UTF-8 / missing company column, `422` per-row errors reported without aborting valid rows | `test_api_import.py` (12 tests) |

Query parameters on `GET /leads`: `query`, `stage`, `industry`, `page`, `page_size`
(1-500). There is deliberately no `status` parameter: `status` is derived from the
canonical `stage`.

---

## 3. Lead intelligence (Module 2)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/leads/{lead_id}/insights` | writer | `200` analysis + `execution` | `404`, `502 ai_failed` when the engine fails, `503 ai_unavailable` when the engine cannot be constructed | `test_insights_generate_persist_and_are_evidence_aware`, `test_insights_unknown_lead_returns_404` |
| GET | `/leads/{lead_id}/insights` | any | `200` stored analyses, newest first | `404` | `test_insights_generate_persist_and_are_evidence_aware` |

Optional request body: `{"product_service": str, "extra_context": str}`.

---

## 4. Outreach (Module 3)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/outreach/generate` | writer | `200` draft + `execution` + campaign `id` | `404`, `422` invalid enumeration, `502 ai_failed` | `test_outreach_generation_persists_a_draft`, `test_outreach_generation_validates_enumerations` |
| POST | `/leads/{lead_id}/outreach-drafts` | writer | `201` campaign | `404` | `test_outreach_draft_can_be_edited_and_marked_sent` |
| GET | `/leads/{lead_id}/outreach-drafts` | any | `200` campaign list | `404` | `test_outreach_generation_persists_a_draft` |
| GET | `/outreach/campaigns/{campaign_id}` | any | `200` campaign | `404` | `test_outreach_missing_campaign_returns_404` |
| PATCH | `/outreach/campaigns/{campaign_id}` | writer | `200` updated campaign | `404` | `test_outreach_draft_can_be_edited_and_marked_sent` |
| POST | `/outreach/campaigns/{campaign_id}/mark-sent` | writer | `200` campaign | `404` | Same test |
| POST | `/outreach/send` | writer | **`501 email_transport_not_configured`** by design (SRS D-05) | — | `test_outreach_send_never_sends_and_reports_501` |

`501` is the expected, documented result. It is not a failure: the build must never claim
to send e-mail when no provider is configured.

---

## 5. Scoring (Module 4)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/leads/{lead_id}/scores` | writer | `200` score, four factors, `conversion_probability: null`, `probability_band`, `probability_note` | `404`, `403` for viewer, `502 ai_failed` | `test_scoring_is_explainable_and_never_fakes_probability`, `test_scoring_requires_write_role` |
| GET | `/leads/{lead_id}/scores` | any | `200` score history | `404` | `test_scoring_history_is_append_only` |
| GET | `/leads/{lead_id}/scores/latest` | any | `200` latest score | `404` before any score exists | `test_latest_score_before_scoring_returns_404` |
| GET | `/recommendations/{lead_id}` | any | `200` recommendation | `404`, `502` | `test_recommendation_endpoint` |

---

## 6. Conversations (Module 5)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| POST | `/conversations/summarize` | writer | `200` summary + `execution` + interaction `id` | `404`, `422` when both transcript and notes are empty, `502` | `test_conversation_summary_persists_interaction`, `test_conversation_requires_content` |
| POST | `/leads/{lead_id}/conversations` | writer | `201` interaction | `404` | `test_conversation_summary_persists_interaction` |
| GET | `/leads/{lead_id}/conversations` | any | `200` interaction list | `404` | Same test |
| GET | `/conversations/{interaction_id}` | any | `200` interaction | `404` | `test_conversation_unknown_lead_returns_404` |

---

## 7. Analytics, follow-ups and CRM (Module 6)

| Method | Path | Role | Success | Error cases verified | Tests |
|---|---|---|---|---|---|
| GET | `/analytics` | any | `200` KPI envelope | — | `test_analytics_returns_only_defensible_metrics` |
| GET | `/dashboard/summary` | any | `200` alias of `/analytics` | — | Hidden alias, same handler |
| POST | `/analytics/snapshot` | manager | `201` stored snapshot | `403` for rep | `test_analytics_snapshot_requires_manager` |
| GET | `/follow-ups` | any | `200` derived follow-up list | — | `test_follow_ups_are_derived_from_stored_scores` |
| POST | `/analytics/insights` | any | `200` observations + disclaimer | `502` | `test_analytics_insights_are_labelled_observations` |
| GET | `/crm/providers` | any | `200` provider configuration state | — | `test_crm_providers_report_configuration_state` |
| POST | `/crm/mappings/validate` | writer | `200` per-field validation result | `422` invalid mapping | `test_crm_mapping_validation` |
| POST | `/crm/sync/preview` | writer | `200` dry-run plan, nothing written | — | `test_crm_sync_preview_is_dry_run` |
| POST | `/crm/sync` | writer | **`501 crm_not_configured`** and a failure row in the sync log | — | `test_crm_sync_records_failure_and_retry` |
| GET | `/crm/sync-logs` | any | `200` log list, newest first | — | `test_crm_sync_records_failure_and_retry` |
| POST | `/crm/sync-logs/{log_id}/retry` | writer | `200` retry result | `404 sync_log_not_found`, `409 already_succeeded` | `test_crm_sync_records_failure_and_retry` |

`conversion_rate` returns a value. `pipeline_value`, `average_response_time_days` and
`average_sales_cycle_days` return `value: null` with `pending_definition: true` while SRS
D-10 is unresolved. A client must render "not defined yet", not `0`.

---

## 8. System routes

| Method | Path | Role | Success |
|---|---|---|---|
| GET | `/api/v1/health` | public | `200 {status, version, database, database_dialect, auth_enabled, ai_backend, ai_status}` |
| GET | `/health` | public | `200`, alias, excluded from the schema |
| GET | `/` | public | `200` service banner |
| GET | `/docs`, `/redoc`, `/openapi.json` | public | Documentation |

---

## 9. Error envelope

Every handled error returns:

```json
{ "detail": "human readable", "code": "machine_readable", "meta": null }
```

Validation errors return `422` with a `detail` list produced by the shared handler. No
endpoint returns a bare HTML error page.

---

## 10. Postman

Import both files from [`../../postman/`](../../postman):

* `SalesGenie-AI.postman_collection.json` - 40 requests grouped by module, with test
  scripts that assert status codes and key fields.
* `SalesGenie-AI.postman_environment.json` - `base_url`, `email`, `password`, `token`,
  `lead_id`, `campaign_id`.

Suggested manual order:

1. **Auth → Issue token.** The collection script stores `token` automatically.
2. **Prospects → Create prospect.** Stores `lead_id`.
3. **Intelligence → Analyze**, then **Read insights**.
4. **Outreach → Generate.** Stores `campaign_id`.
5. **Scoring → Score lead**, then **Latest score**.
6. **Conversations → Summarize**.
7. **Analytics → KPIs**, **Follow-ups**.
8. **CRM → Providers**, **Preview**, **Sync** (expect `501`), **Sync logs**.

The Postman collection is a manual/exploratory aid. The authoritative automated result is
the pytest suite and the live UAT runner; Postman results are not counted as passing tests
in [`milestone-test-report.md`](milestone-test-report.md).
