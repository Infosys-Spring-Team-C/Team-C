# Live UAT run

- **Executed:** 2026-11-17 14:08:52 UTC
- **Target:** `http://127.0.0.1:8011`
- **Operator:** `qa.admin@example.com`
- **Workflows:** 25
- **Result:** 25 passed, 0 partial, 0 failed

| ID | Workflow | Requirement | Status | ms |
|---|---|---|---|---|
| UAT-01 | Health and readiness | NFR-011 | **PASS** | 5 |
| UAT-02 | Administrator can sign in | FR-001 / D-04 | **PASS** | 246 |
| UAT-03 | Wrong password is refused | NFR-005 | **PASS** | 228 |
| UAT-04 | Unauthenticated access is refused | NFR-005 | **PASS** | 5 |
| UAT-05 | Create a prospect manually | FR-001, FR-009 | **PASS** | 20 |
| UAT-06 | Duplicate detection | FR-008 | **PASS** | 16 |
| UAT-07 | List, search and paginate prospects | FR-002 | **PASS** | 22 |
| UAT-08 | Move a prospect between lifecycle stages | FR-005 | **PASS** | 16 |
| UAT-09 | Import prospects from CSV | FR-007, FR-008 | **PASS** | 23 |
| UAT-10 | Invalid input is rejected cleanly | AC-005 | **PASS** | 6 |
| UAT-11 | Company intelligence is generated and stored | FR-011..FR-016 | **PASS** | 22 |
| UAT-12 | Outreach is generated, edited and retrieved | FR-019..FR-026 | **PASS** | 34 |
| UAT-13 | Send is visibly unavailable, not faked | FR-024 / D-05 | **PASS** | 6 |
| UAT-14 | Lead score is explainable and honest | FR-028..FR-031 | **PASS** | 22 |
| UAT-15 | Next-best-action recommendation | FR-032 | **PASS** | 7 |
| UAT-16 | Conversation notes are summarised and stored | FR-036..FR-039 | **PASS** | 21 |
| UAT-17 | CRM sync fails safely and is logged | FR-043, FR-045 | **PASS** | 38 |
| UAT-18 | Dashboard KPIs are computed or honestly withheld | FR-046..FR-050 | **PASS** | 14 |
| UAT-19 | Follow-up panel data | FR-052 | **PASS** | 11 |
| UAT-20 | Role-based access control | NFR-005 | **PASS** | 466 |
| UAT-21 | Delete a prospect | FR-004 | **PASS** | 19 |
| UAT-22 | CRM field mappings cover both providers | FR-040 | **PASS** | 18 |
| UAT-23 | Simulated CRM sync covers contact, activity and deal stage | FR-041..FR-043 | **PASS** | 84 |
| UAT-24 | An invalid CRM operation is refused and not audited | FR-041, AC-024 | **PASS** | 52 |
| UAT-25 | Conversations page data contract | FR-044, AC-023 | **PASS** | 48 |

## Detail

### UAT-01 - Health and readiness (PASS)

- health={"ai_backend": "heuristic", "ai_mode": "live-model", "ai_model": "deterministic-heuristic-v1", "ai_note": "", "ai_provider": "heuristic", "ai_status": "ok", "ai_used_mock": false, "auth_enabled": true, "database": "ok", "database_dialect": "sqlite", "status": "ok", "version": "1.0.0"}

### UAT-02 - Administrator can sign in (PASS)

- token_type=bearer expires_in=7200
- me={"created_at": "2026-11-17T14:07:19.680400", "email": "qa.admin@example.com", "full_name": "QA Admin", "id": 1, "is_active": true, "role": "admin"}

### UAT-03 - Wrong password is refused (PASS)

- body={"detail":"Incorrect email or password.","code":"invalid_credentials","meta":null}

### UAT-04 - Unauthenticated access is refused (PASS)

- body={"detail":"Not authenticated.","code":"not_authenticated","meta":null}

### UAT-05 - Create a prospect manually (PASS)

- created lead id=6 stage=qualified status=Active

### UAT-06 - Duplicate detection (PASS)

- duplicate-check={"is_duplicate": true, "match_reason": "email", "matched_lead_id": "6"}

### UAT-07 - List, search and paginate prospects (PASS)

- X-Total-Count=5 X-Page=1 X-Page-Size=5
- search returned 1 row(s)

### UAT-08 - Move a prospect between lifecycle stages (PASS)

- stage=proposal status=Active

### UAT-09 - Import prospects from CSV (PASS)

- import report={"filename": "uat-leads.csv", "imported": 2, "duplicates": 1, "invalid": 0, "total_rows": 3, "errors": [{"row": 4, "error": "email already belongs to lead 6"}], "duplicate_rows": [4], "skipped": 1}

### UAT-10 - Invalid input is rejected cleanly (PASS)

- body={"detail":"Request validation failed.","code":"validation_error","meta":null,"errors":[{"loc":["body","company_name"],"msg":"String should have at least 1 character","type":"string_too_short"},{"loc":

### UAT-11 - Company intelligence is generated and stored (PASS)

- provider=heuristic needs=1 opportunities=1
- persisted insight rows=1

### UAT-12 - Outreach is generated, edited and retrieved (PASS)

- campaign id=1 channel=Email body_chars=213
- draft edit accepted
- history rows=1

### UAT-13 - Send is visibly unavailable, not faked (PASS)

- code=email_transport_not_configured detail=No e-mail delivery provider is configured. Outreach content can be generated, edited and exported, but this build never sends e-mail. See SRS decision D-05.

### UAT-14 - Lead score is explainable and honest (PASS)

- score=90 priority=hot probability=None model=heuristic:deterministic-heuristic-v1
- latest score id=1

### UAT-15 - Next-best-action recommendation (PASS)

- priority=High timing='Within one business day'
- channel field(s) present: ['suggested_channel']

### UAT-16 - Conversation notes are summarised and stored (PASS)

- summary='Call with Ada Fernandes, 24 Oct 2026. Discussed dispatch backlog and driver turnover. Ada will send the current routing ' points=4 actions=1
- stored interactions=1

### UAT-17 - CRM sync fails safely and is logged (PASS)

- code=crm_not_configured meta={'sync_log_id': 3}
- sync log rows 2 -> 3

### UAT-18 - Dashboard KPIs are computed or honestly withheld (PASS)

- total_leads=7 conversion_rate=0.0 pipeline_value=None pending=True

### UAT-19 - Follow-up panel data (PASS)

- rows=1 first_priority=hot

### UAT-20 - Role-based access control (PASS)

- created viewer id=3
- viewer write denied with 403
- viewer read allowed
- viewer user administration denied

### UAT-21 - Delete a prospect (PASS)

- delete returned 204 and the record is gone

### UAT-22 - CRM field mappings cover both providers (PASS)

- providers=salesforce,hubspot entities=contact,activity,deal
- operations=['activity_log', 'sync_contact', 'update_stage', 'upsert']
- unknown provider -> 422 invalid_provider

### UAT-23 - Simulated CRM sync covers contact, activity and deal stage (PASS)

- sync_contact: record_type=contact external_id=sim-salesforce-0f9986b748
- activity_log: record_type=activity external_id=sim-salesforce-0f9986b748
- update_stage: record_type=deal external_id=sim-salesforce-0f9986b748
- audit rows verified: [4, 5, 6]

### UAT-24 - An invalid CRM operation is refused and not audited (PASS)

- 422 invalid_operation; sync log rows stayed at 6
- status={"connectivity": "simulated", "recent_failures": 2, "recent_syncs": 6}

### UAT-25 - Conversations page data contract (PASS)

- interaction id=2 points=3 actions=1
- api_compat maps interaction_date -> created_at for the page
