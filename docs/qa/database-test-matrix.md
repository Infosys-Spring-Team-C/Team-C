# Database Test Matrix

**Date:** 26 October 2026
**Author:** Mohamed Isharak M
**Schema owner (as designed):** Marri Sai Surekha
**Migration:** `alembic/versions/0001_canonical_schema.py`
**Status of this schema:** provisional until the database owner's work is merged

---

## 1. Environments

| ID | Engine | Version | Purpose |
|---|---|---|---|
| DB-SQLITE | SQLite (file) | Python 3.10.11 bundled | Fast regression, default suite |
| DB-PG | PostgreSQL | 16.15, isolated cluster on port 55432 | Production dialect, JSONB, real constraints |
| DB-UAT | PostgreSQL | 16.15, database `salesgenie_uat` | Live UAT persistence |

Both dialects run the **same** ORM and migration code. Dialect-specific behaviour is
tested explicitly in `tests/test_postgres.py`, which is skipped automatically when
`TEST_DATABASE_URL` is not set (this is the reason for the `6 skipped` in the SQLite run).

---

## 2. Tables under test

| Table | Purpose | PK | Foreign keys | Delete behaviour |
|---|---|---|---|---|
| `users` | Authentication and RBAC principals | `id` | none | — |
| `leads` | Prospect master record | `id` | `owner_id → users.id` | `SET NULL` when the owner is removed |
| `company_insights` | Stored Module 2 intelligence | `id` | `lead_id → leads.id` | `CASCADE` |
| `outreach_campaigns` | Generated and edited outreach | `id` | `lead_id → leads.id` | `CASCADE` |
| `lead_scores` | Append-only score history | `id` | `lead_id → leads.id` | `CASCADE` |
| `sales_interactions` | Conversation summaries and notes | `id` | `lead_id → leads.id` | `CASCADE` |
| `crm_sync_logs` | CRM synchronisation attempts | `id` | `lead_id → leads.id` | `SET NULL` so the audit row survives |
| `sales_analytics` | Stored analytics snapshots | `id` | none | — |

Six foreign keys in total. `sales_analytics` intentionally has no foreign key: a snapshot
is a point-in-time aggregate, not a per-lead row.

---

## 3. Constraint tests

| ID | Constraint | Expected behaviour | Test | Verdict |
|---|---|---|---|---|
| DB-C-01 | `users.email` unique | Second insert with the same e-mail is rejected | `test_api_auth.py::test_admin_can_create_user_and_non_admin_cannot` (`409`) | PASS |
| DB-C-02 | `leads.email_key` unique | Second lead with the same normalised e-mail is rejected | `test_schema.py::test_email_key_uniqueness_is_enforced`, `test_postgres.py::test_unique_email_key_is_enforced_on_postgres` | PASS |
| DB-C-03 | `leads.email_key` nullable | Multiple leads without an e-mail do not collide | `test_schema.py::test_leads_without_email_do_not_collide` | PASS |
| DB-C-04 | `company_insights.lead_id` NOT NULL + FK | Insert without a valid lead is rejected | `test_schema.py::test_migration_matches_orm_metadata` | PASS |
| DB-C-05 | `outreach_campaigns.lead_id` NOT NULL + FK | Same | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| DB-C-06 | `lead_scores.lead_id` NOT NULL + FK | Same | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| DB-C-07 | `sales_interactions.lead_id` NOT NULL + FK | Same | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| DB-C-08 | `leads.owner_id` nullable + `SET NULL` | Deleting the owner keeps the lead and nulls the owner | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| DB-C-09 | `crm_sync_logs.lead_id` nullable + `SET NULL` | Deleting the lead keeps the audit log | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |
| DB-C-10 | `lead_scores.score` bounded 0-100 at the API layer | Out-of-range score rejected before storage | `test_intelligence.py::test_score_factor_bounds_are_validated` | PASS (application-enforced) |

---

## 4. CRUD and relationship tests

| ID | Operation | Expected | Test | Verdict |
|---|---|---|---|---|
| DB-R-01 | Create a lead and read it back through a fresh session | All fields round-trip | `test_postgres.py::test_orm_round_trip_and_cascade_on_postgres` | PASS |
| DB-R-02 | Create lead + insight + campaign + score + interaction, then delete the lead | All four dependants removed | `test_schema.py::test_cascade_delete_removes_dependent_rows`, `test_postgres.py::test_orm_round_trip_and_cascade_on_postgres` | PASS |
| DB-R-03 | Update a lead field and stage | Change persisted, `updated_at` advances | `test_api_leads.py::test_patch_lead_updates_fields_and_stage` | PASS |
| DB-R-04 | Delete a lead through the API | Row removed, dependent rows removed, `404` afterwards | UAT-21 | PASS |
| DB-R-05 | Store and retrieve JSON columns | Structured values round-trip unchanged | `test_schema.py::test_json_columns_round_trip` | PASS |
| DB-R-06 | Store and retrieve JSONB on PostgreSQL | Structured values round-trip unchanged | `test_postgres.py::test_jsonb_columns_accept_structured_values` | PASS |
| DB-R-07 | Score history grows without mutating earlier rows | Row count increases, prior rows unchanged | `test_api_ai.py::test_scoring_history_is_append_only` | PASS |
| DB-R-08 | CRM sync log survives lead deletion | Log row remains with `lead_id` nulled | `test_postgres.py::test_foreign_keys_use_cascade_and_set_null` | PASS |

---

## 5. Migration tests

| ID | Test | Expected | Actual |
|---|---|---|---|
| DB-M-01 | `alembic upgrade head` on an empty SQLite database | Schema created, no error | PASS |
| DB-M-02 | `alembic upgrade head` on an empty PostgreSQL 16 database | Schema created, no error | PASS - executed on `salesgenie_uat` |
| DB-M-03 | `alembic downgrade base` on PostgreSQL 16 | All eight tables dropped cleanly | PASS - executed during UAT setup |
| DB-M-04 | Migration output equals ORM metadata | No drift between models and migration | PASS - `test_migration_matches_orm_metadata` |
| DB-M-05 | Migration creates exactly the eight canonical tables | Set equality, no extras | PASS - `test_migration_created_all_tables` |
| DB-M-06 | Expected indexes exist on PostgreSQL | Index set present | PASS - `test_indexes_exist_on_postgres` |

The upgrade → downgrade → upgrade cycle was executed on PostgreSQL during UAT setup and
the application started and served traffic afterwards, so the migration is reversible in
practice, not only in theory.

---

## 6. Dialect parity

| Behaviour | SQLite | PostgreSQL 16 | Test |
|---|---|---|---|
| Eight tables | PASS | PASS | `test_schema.py`, `test_postgres.py` |
| Unique e-mail key | PASS | PASS | Both suites |
| Cascade delete | PASS | PASS | Both suites |
| `SET NULL` on owner / sync log | PASS | PASS | `test_postgres.py` |
| JSON storage | `TEXT`-backed JSON | `JSONB` | Both suites |
| Timestamp defaults | Application-side | `now()` with time zone | Both suites |
| Null ordering in list queries | PASS | PASS | `test_api_leads.py` |

---

## 7. Data integrity checks performed

1. **No orphan rows.** Every child insert requires an existing parent; the FK rejects it
   otherwise.
2. **No duplicate prospects.** `email_key` is unique; blank e-mails are stored as `NULL`
   so they do not collide.
3. **No silent data loss on delete.** Child rows cascade; audit rows survive via `SET NULL`.
4. **No fabricated analytics.** KPI columns that would need a business definition are
   returned as `null` with `pending_definition: true`; the database is never seeded with
   zeros to make a dashboard look populated.
5. **Append-only history.** `lead_scores` rows are inserted, never updated in place.
6. **Uncalibrated probability.** `lead_scores.conversion_probability` is `NULL` for the
   heuristic engine, so no query can later mistake it for a trained model output.

---

## 8. Known schema risks

| Risk | Impact | Status |
|---|---|---|
| Schema is provisional pending the database owner's merge | Database tests will need re-baselining | Open - tracked in the test plan |
| The database owner's written ER description and her `init_schema.sql` disagree on column widths, uniqueness and cascade rules | The merged schema may not match either document | **BUG-009** |
| `VARCHAR(15)` for a phone number in the proposed design is too short for international formats | Import and manual entry failures | **BUG-010** |
| No delete policy is defined for `users` | Owner references rely on `SET NULL`; a hard delete of a user is untested | Open - low |
| Free-text lifecycle status in the proposed design | Stage filtering becomes unreliable | Mitigated here by the canonical seven-stage list |

---

## 9. Database test inventory

| Suite | Tests | Requires PostgreSQL |
|---|---|---|
| `tests/test_schema.py` | 8 | No |
| `tests/test_postgres.py` | 6 | Yes |
| Database assertions inside API suites | Included in the 29 AI and 19 lead tests | No |

Totals from the verified runs: **111 passed, 6 skipped** on SQLite and **117 passed** on
PostgreSQL 16. See [`evidence/`](evidence/).
