# Software Requirements Specification (SRS)

## SalesGenie AI — AI Sales Assistant & Lead Intelligence Platform

---

## 1. Document Control

| Field | Value |
|---|---|
| Document title | Software Requirements Specification (SRS) |
| Document ID | DOC-SRS |
| Version | 1.0 |
| Status | Draft for team review |
| Date | 22 October 2026 |
| Owner | Mohamed Isharak M (Project Lead / Scrum Master) |
| Contributors | M Doran, Marri Sai Surekha, Mahidhar Reddy, Maheksaba Akbar Shaikh |
| Purpose | Define the complete, testable requirements for SalesGenie AI as the baseline for architecture, design, implementation, testing and milestone acceptance. |
| Source of truth | SalesGenie AI Master Context (project facts) |

### Revision history

| Version | Date | Author | Summary of change |
|---|---|---|---|
| 1.0 | 22 October 2026 | Mohamed Isharak M | Initial draft covering six modules, NFRs, use cases, acceptance criteria and traceability. |

### How to read this document

- **Confirmed** — stated directly in the master context (project identity, modules, team, schedule).
- **Planned** — intended functionality or target that has been agreed but is not yet implemented or verified.
- **Proposed** — a recommendation made by this document, awaiting team approval.
- **[TO BE CONFIRMED]** — an unresolved decision; see Section 16 and the Decision Register.

No content in this document should be read as evidence that code, tests or integrations already exist.

---

## 2. Executive Summary and Project Purpose

**SalesGenie AI** is an AI Sales Assistant & Lead Intelligence Platform built as an academic software project by a five-person student team. The project runs from **12 October 2026 to 20 November 2026** (40 calendar days: 30 weekdays and 10 weekend buffer/testing days) under a compressed six-module, four-milestone plan.

**Purpose.** The platform is intended to help sales teams manage prospects, understand target companies, generate AI-assisted outreach, prioritize leads through scoring, capture conversation insights, and monitor sales performance — in a single workspace.

**Planned value proposition:**

- Replace fragmented lead tracking with a structured lead-management workflow.
- Provide AI-generated company and industry intelligence alongside lead records.
- Reduce manual effort in writing personalized outreach.
- Give sales representatives a ranked view of leads and a recommended next action.
- Turn meeting/call notes into stored, searchable sales interactions.
- Present sales KPIs and a visual pipeline for management review.

**Current status (22 October 2026):** this is a requirements baseline for a project in progress. The schedule tracker records the first 11 days as *In Progress* and zero days as *Completed*; no implementation has been independently verified through this document.

---

## 3. Problem Statement and Proposed Solution

### 3.1 Problem statement

Sales teams and student-led sales workflows typically suffer from:

1. **Fragmented prospect data** — contact and company details scattered across spreadsheets with duplicates and inconsistent lifecycle stages.
2. **Slow lead research** — understanding a company's business needs, industry position and qualification signals takes manual effort per lead.
3. **Time-consuming outreach** — writing personalized emails for many prospects is repetitive and inconsistent in tone and quality.
4. **Subjective prioritization** — without scoring, representatives guess which leads deserve attention first.
5. **Lost conversation context** — meeting and call notes rarely become structured action items or CRM records.
6. **Limited visibility** — management lacks a real-time view of conversion rate, pipeline value and follow-up obligations.

### 3.2 Proposed solution

SalesGenie AI proposes an integrated platform of six modules (see Section 6) backed by a Streamlit frontend, a FastAPI backend, Python services (including AI/LLM services), and a PostgreSQL database, deployed with Docker. AI capabilities (company analysis, outreach generation, lead scoring, conversation summarization) are planned to be delivered through LangGraph agents and an LLM provider **[TO BE CONFIRMED — provider selection, Decision D-01]**.

---

## 4. Project Objectives and Measurable Success Criteria

| Obj ID | Objective | Success criterion | Target | Status of target |
|---|---|---|---|---|
| OBJ-1 | Deliver complete Lead Management functionality by Milestone 1 | Records manageable through UI/API (create, read, update, delete, import) | ≥ 95% of test records manageable | Planned (Milestone 1 acceptance) |
| OBJ-2 | Deliver accurate lead intelligence | Intelligence outputs judged accurate against agreed test set | "Accurate insights" — definition pending (Decision D-13) | Planned, metric undefined |
| OBJ-3 | Deliver AI outreach, scoring and recommendations by Milestone 2 | Scoring accuracy against agreed test dataset | ≥ 85% | Planned, metric undefined (Decision D-13) |
| OBJ-4 | Deliver CRM integration, summarization and conversations by Milestone 3 | Integrated demo with sign-off | Milestone sign-off by 10 November 2026 | Planned |
| OBJ-5 | Deliver analytics, UAT, deployment and documentation by Milestone 4 | UAT satisfaction survey | ≥ 85% | Planned, survey definition pending (Decision D-12) |
| OBJ-6 | Meet responsiveness expectations | Lead analysis and outreach response time | < 5 seconds | Planned, measurement conditions pending (Decision D-11) |
| OBJ-7 | Complete within the fixed calendar window | Final delivery | 20 November 2026 | Planned |

> Note: targets marked "metric undefined" cannot be evaluated until the team approves the dataset, denominator and measurement method. See Section 14 and `docs/test-plan.md`.

---

## 5. Stakeholders, User Roles and Intended Users

### 5.1 Stakeholders

| Stakeholder | Interest |
|---|---|
| Academic institution / evaluators | Project completion, demonstration, documentation quality |
| Project team (5 members) | Delivery, learning, role fulfilment |
| Project lead — Mohamed Isharak M | Planning, demos, sign-off, QA |
| End users (proposed) | Sales representatives and sales managers using the platform |
| External service providers (planned) | LLM provider, CRM vendors (Salesforce/HubSpot), possible email delivery provider |

### 5.2 User roles

The master context confirms **JWT/RBAC for access control is listed in team responsibilities but the authorization design is unverified (Decision D-04)**. The following roles are therefore **proposed**, not confirmed:

| Role ID | Role | Description | Status |
|---|---|---|---|
| UR-01 | Sales Representative | Creates/edits leads, generates outreach, reviews scores, logs interactions | Proposed |
| UR-02 | Sales Manager | Views analytics dashboard, pipeline, team follow-ups | Proposed |
| UR-03 | Administrator | Manages users, settings and integrations | Proposed |

*No additional user roles, permissions or business rules beyond the above are specified. Detailed role-permission mappings are deferred until Decision D-04 is resolved.*

### 5.3 Intended users

Primary intended users of the platform: sales representatives and sales managers in a small-team setting, plus the academic evaluator reviewing the system during demonstrations.

---

## 6. Project Scope

### 6.1 In-scope functionality

Six product modules (names used consistently across all project documents):

| Module ID | Module name | Scope summary |
|---|---|---|
| M1 | Lead Management | Prospect CRUD, lifecycle stages, manual and CSV import, duplicate detection, persistence, Leads UI |
| M2 | Company Analysis / Lead Intelligence | Company profile analysis, business needs, opportunities, industry insights, qualification info, storage and display alongside leads |
| M3 | AI Outreach Generation | Personalized outreach with tone/length/type/goal/pain-point/industry inputs; generate, refresh, edit, copy; planned send; campaign storage |
| M4 | Lead Scoring and Recommendations | Lead scores, conversion-probability estimates (engagement, fit, intent, decision readiness), score storage, next-best-action recommendations |
| M5 | Conversation Intelligence / CRM Integration | Meeting/call summarization, key points and action items, interaction storage, planned Salesforce/HubSpot field mapping and sync, CRM sync logs |
| M6 | Sales Analytics Dashboard | KPI cards (conversion rate, pipeline value, average response time, average sales cycle), Kanban-style pipeline, follow-up recommendations panel |

### 6.2 Explicit exclusions

- Native mobile applications.
- Automated email delivery beyond the planned "send" action (provider unconfirmed — Decision D-05); until confirmed, send is UI-planned only.
- Verified production CRM integrations — credentials and API access are not confirmed (Decision D-06).
- Custom-trained machine-learning models; scoring is planned to be model/LLM-based, not a trained in-house model.
- Multi-tenant SaaS packaging, billing and licensing.
- Any functionality not listed in Section 6.1.

### 6.3 Dependencies

| Dep ID | Dependency | Type | Owner | Status |
|---|---|---|---|---|
| DEP-01 | LLM provider API access and key | External | Mahidhar Reddy | Unconfirmed (D-01) |
| DEP-02 | PostgreSQL server availability | Infrastructure | Marri Sai Surekha | Planned |
| DEP-03 | Salesforce/HubSpot API access & credentials | External | Mohamed Isharak M | Unconfirmed (D-06) |
| DEP-04 | Email delivery provider (for send action) | External | M Doran | Unconfirmed (D-05) |
| DEP-05 | GitHub organization and team communication | Tooling | Mohamed Isharak M | Confirmed established |
| DEP-06 | Jira/Trello for task tracking | Tooling | Mohamed Isharak M | Listed in team toolset |
| DEP-07 | Docker runtime for deployment | Infrastructure | Marri Sai Surekha | Planned (D-14) |
| DEP-08 | Agreed scoring/accuracy and UAT test datasets | Internal | Mohamed Isharak M | Not yet defined (D-12, D-13) |

---

## 7. Functional Requirements

IDs FR-001 … FR-053 are stable. Owner column uses the confirmed team assignments; "[TO BE CONFIRMED]" marks ownership not established by the master context.

### 7.1 Module 1 — Lead Management (FR-001 – FR-010)

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | The system shall allow a user to create a new prospect (lead) record with the required prospect details. | Must |
| FR-002 | The system shall allow a user to retrieve and view the list of prospects and the detail of an individual prospect. | Must |
| FR-003 | The system shall allow a user to update an existing prospect record. | Must |
| FR-004 | The system shall allow a user to delete a prospect record. | Must |
| FR-005 | The system shall support lead lifecycle stages and allow a prospect to be moved between stages. *(Exact stage list: [TO BE CONFIRMED])* | Must |
| FR-006 | The system shall allow a user to add a lead manually through the Leads UI. | Must |
| FR-007 | The system shall allow a user to import leads from a CSV file. *(CSV column mapping: [TO BE CONFIRMED])* | Must |
| FR-008 | The system shall detect duplicate leads during creation and CSV import and report them to the user. *(Duplicate rule: [TO BE CONFIRMED — proposed match on email and/or company+contact name])* | Must |
| FR-009 | The system shall persist prospect data and retrieve it in later sessions. | Must |
| FR-010 | The system shall make prospect data retrievable for use by Modules 2, 3, 4, 5 and 6 through internal service/API access. | Must |

### 7.2 Module 2 — Company Analysis / Lead Intelligence (FR-011 – FR-018)

| ID | Requirement | Priority |
|---|---|---|
| FR-011 | The system shall accept a company profile as input for analysis (from prospect data and/or user-provided fields). | Must |
| FR-012 | The system shall produce business-needs analysis for the company. | Must |
| FR-013 | The system shall produce identified business opportunities for the company. | Must |
| FR-014 | The system shall produce relevant industry insights for the company. | Must |
| FR-015 | The system shall generate lead qualification information as intelligence output. | Must |
| FR-016 | The system shall store intelligence output against the associated lead. | Must |
| FR-017 | The system shall display intelligence alongside the associated lead record in the UI. | Must |
| FR-018 | The system shall validate intelligence output before storage and handle AI provider failure gracefully, surfacing a clear error state without corrupting existing data. | Must |

### 7.3 Module 3 — AI Outreach Generation (FR-019 – FR-027)

| ID | Requirement | Priority |
|---|---|---|
| FR-019 | The system shall generate a personalized sales email/outreach for a selected lead. | Must |
| FR-020 | The generation request shall accept the following prompt inputs: **tone, length, outreach type, goal, pain points and industry**. | Must |
| FR-021 | The system shall support refreshing/regenerating outreach to produce a new variant. | Must |
| FR-022 | The system shall allow the user to edit a generated outreach before use. | Must |
| FR-023 | The system shall allow the user to copy outreach content to the clipboard. | Must |
| FR-024 | The system shall provide a send action for outreach. **Planned only** — email delivery provider and actual send implementation are unconfirmed (Decision D-05); behavior is [TO BE CONFIRMED]. | Should |
| FR-025 | The system shall store outreach campaigns. | Must |
| FR-026 | The system shall retrieve outreach history for a lead/campaign. | Must |
| FR-027 | The Outreach UI shall present generate, refresh, edit, copy and send actions to the user. | Must |

### 7.4 Module 4 — Lead Scoring and Recommendations (FR-028 – FR-035)

| ID | Requirement | Priority |
|---|---|---|
| FR-028 | The system shall produce a lead score for a prospect. *(Score scale: [TO BE CONFIRMED — proposed 0–100], Decision D-09)* | Must |
| FR-029 | The system shall produce a conversion-probability estimate for a prospect. *(Format: [TO BE CONFIRMED — proposed 0.00–1.00], Decision D-09)* | Must |
| FR-030 | Scoring shall consider the four confirmed factors: **engagement, fit, intent and decision readiness**. Weighting per factor is [TO BE CONFIRMED]. | Must |
| FR-031 | The system shall store lead scores (with enough history to show change over time — history depth [TO BE CONFIRMED]). | Must |
| FR-032 | The system shall generate next-best-action recommendations including **follow-up timing, channel and content strategy**. | Must |
| FR-033 | The system shall display the score and its recommendation in the UI. | Must |
| FR-034 | The system shall support accuracy validation of scores against an agreed test dataset using an agreed metric (Decision D-13). | Must |
| FR-035 | The system shall handle missing or incomplete lead data during scoring by producing a defined degraded outcome (e.g., score withheld or flagged) rather than an unhandled error. *Behavior [TO BE CONFIRMED]* | Should |

### 7.5 Module 5 — Conversation Intelligence / CRM Integration (FR-036 – FR-045)

| ID | Requirement | Priority |
|---|---|---|
| FR-036 | The system shall summarize meeting and call notes supplied by the user. | Must |
| FR-037 | The system shall extract key discussion points from notes. | Must |
| FR-038 | The system shall extract action items from notes. | Must |
| FR-039 | The system shall store sales interactions. | Must |
| FR-040 | The system shall support field mapping between SalesGenie AI fields and CRM fields. **Planned** — CRM access unconfirmed (Decision D-06); exact mapping [TO BE CONFIRMED]. | Should |
| FR-041 | The system shall support synchronization of contacts and activities with the CRM. **Planned**, unconfirmed (D-06). | Should |
| FR-042 | The system shall support synchronization of deal stage with the CRM. **Planned**, unconfirmed (D-06). | Should |
| FR-043 | The system shall record CRM synchronization logs (attempt, outcome, timestamp, error detail). | Must |
| FR-044 | The Conversations UI shall allow a user to enter notes and view stored summaries, discussion points and action items. | Must |
| FR-045 | The system shall handle CRM synchronization failures by recording the failure in the sync log and surfacing a clear error to the user, without losing the local interaction record. | Must |

### 7.6 Module 6 — Sales Analytics Dashboard (FR-046 – FR-053)

| ID | Requirement | Priority |
|---|---|---|
| FR-046 | The dashboard shall display **conversion rate**. *(Formula/denominator: [TO BE CONFIRMED], Decision D-10)* | Must |
| FR-047 | The dashboard shall display **pipeline value**. *(Definition of value source: [TO BE CONFIRMED], D-10)* | Must |
| FR-048 | The dashboard shall display **average response time**. *(Definition of "response": [TO BE CONFIRMED], D-10)* | Must |
| FR-049 | The dashboard shall display **average sales cycle**. *(Definition of cycle start/end: [TO BE CONFIRMED], D-10)* | Must |
| FR-050 | The dashboard shall present KPI cards. | Must |
| FR-051 | The dashboard shall present a Kanban-style sales pipeline visualization. | Must |
| FR-052 | The dashboard shall include a follow-up recommendations panel. | Must |
| FR-053 | The dashboard shall render correctly with an empty dataset and shall present values consistent with the database records. | Must |

> **Ownership gap (open):** the master context assigns M Doran API-layer work for Modules 1, 3, 4 and 5, and Maheksaba Akbar Shaikh the Module 6 dashboard — but the owner of the Module 2 service/API layer and the Module 6 analytics computation layer is not explicitly assigned. Recorded as Decisions D-07 and D-08.

---

## 8. Non-Functional Requirements

| ID | Category | Requirement | Verification |
|---|---|---|---|
| NFR-001 | Performance | Lead analysis and outreach generation shall complete in under 5 seconds. Measurement conditions (dataset, network, warm/cold start, provider latency) are undefined — Decision D-11. | TC-PERF-001, TC-PERF-002 |
| NFR-002 | Reliability | Failures of the AI provider or database shall be handled gracefully: no data loss, no unhandled crash, user-visible error message. | TC-M2-005, TC-DB-004, TC-API-005 |
| NFR-003 | Usability | A sales user shall be able to complete lead creation, analysis, outreach generation and dashboard review without training beyond the in-app documentation. Navigation structure is unresolved (4 tabs vs 6 sidebar functions — Decision D-03). | UAT (Milestone 4) |
| NFR-004 | Maintainability | Business logic, AI logic and persistence shall be separated into modules/services; configuration shall be externalized from code; code shall be documented sufficiently for another team member to modify it. | Architecture review, code review |
| NFR-005 | Security | Access control shall use authentication and authorization as designed under Decision D-04 (JWT/RBAC listed, unverified). No secrets shall be stored in source control. | TC-SEC-001 … TC-SEC-004 |
| NFR-006 | Privacy | Prospect personal data shall be stored only in the project database, not logged in plain text or committed to the repository. | TC-SEC-001 |
| NFR-007 | Testability | Each functional requirement shall be traceable to at least one test case; core logic shall be testable with Pytest without manual intervention. | RTM completeness check |
| NFR-008 | Data integrity | Constraints and duplicate detection shall prevent invalid/duplicate prospect records; multi-step operations shall be transactional where applicable. | TC-DB-002, TC-DB-003, TC-M1-009 |
| NFR-009 | Scalability | The system shall remain responsive for a small-team dataset (hundreds to low-thousands of leads). Exact volume target: [TO BE CONFIRMED]. | TC-PERF-001 |
| NFR-010 | Auditability | CRM synchronization attempts and outcomes shall be logged (FR-043); outreach and score history shall be reviewable. | TC-M5-009 |
| NFR-011 | Deployability | The application shall be deployable via Docker as planned (topology under Decision D-14). Deployment must not be claimed as working until verified. | TC-DEP-001 |
| NFR-012 | Observability | Application errors and AI provider call outcomes shall be written to logs sufficient for debugging (log format/destination [TO BE CONFIRMED]). | Code review |

---

## 9. Data Requirements and High-Level Entities

Confirmed conceptual entities named by the project context (not verified as implemented tables):

| Entity ID | Entity | Purpose | Module(s) |
|---|---|---|---|
| ENT-01 | Prospect / Lead | Core record of a potential customer | M1 (all others depend on it) |
| ENT-02 | Company Insight | Stored intelligence output for a company/lead | M2 |
| ENT-03 | Outreach Campaign | Generated outreach content and metadata | M3 |
| ENT-04 | Lead Score | Score, probability and recommendation | M4 |
| ENT-05 | Sales Interaction | Meeting/call record, summary, points, actions | M5 |
| ENT-06 | CRM Sync Log | Record of CRM synchronization attempts | M5 |
| ENT-07 | Sales Analytics storage | Aggregated KPI/pipeline data for the dashboard | M6 |

Additional entities (e.g., User/Account for authentication, import batch records, recommendation history) are **proposed** and depend on Decisions D-02 and D-04. Detailed schema is specified separately in `docs/database-design.md`.

**Data handling requirements:**

- Prospect data must survive service restarts (FR-009).
- Generated intelligence, outreach and scores must be linked to the originating lead.
- Analytics must be derivable from stored records (FR-053) — whether via stored aggregates or computed queries is [TO BE CONFIRMED] (D-02).

---

## 10. External Integrations and Third-Party Dependencies

| ID | Integration | Purpose | Modules | Status |
|---|---|---|---|---|
| INT-01 | LLM provider (Gemini / OpenAI / Groq — conflicting references) | Company analysis, outreach generation, scoring support, summarization | M2, M3, M4, M5 | Planned; provider unconfirmed (D-01) |
| INT-02 | LangGraph | Agent orchestration for AI workflows | M2, M3, M4, M5 | Planned technology |
| INT-03 | Salesforce CRM | Contact/activity/deal-stage sync | M5 | Planned; credentials/API access unverified (D-06) |
| INT-04 | HubSpot CRM | Contact/activity/deal-stage sync | M5 | Planned; credentials/API access unverified (D-06) |
| INT-05 | Email delivery provider | Outreach send action | M3 | Unconfirmed; may not exist in v1.0 (D-05) |
| INT-06 | PostgreSQL | Primary datastore | All | Planned |
| INT-07 | GitHub | Source control (organization established) | All | Confirmed (organization established; repository state unverified) |

**Constraint:** no integration in this table may be described as functional until verified by QA.

---

## 11. System Constraints and Assumptions

### 11.1 Constraints

| ID | Constraint |
|---|---|
| CON-01 | Fixed delivery window: 12 October – 20 November 2026 (40 calendar days). |
| CON-02 | Team size: exactly five members with fixed role assignments. |
| CON-03 | Intended technology stack: Streamlit, FastAPI, Python, PostgreSQL, SQLAlchemy, Pydantic, LangGraph, LLM provider, Docker, Pytest, Postman. |
| CON-04 | Budget/licensing for external APIs is [TO BE CONFIRMED]; free-tier or academic access assumptions must be validated. |
| CON-05 | Project is academic; scope changes require lead approval (see `docs/project-plan.md` change process). |

### 11.2 Assumptions

| ID | Assumption | Validation owner |
|---|---|---|
| AS-01 | Each member can dedicate sufficient daily time across the 40-day window. | Mohamed Isharak M |
| AS-02 | An LLM provider key with sufficient quota will be available for development and evaluation. | Mahidhar Reddy |
| AS-03 | PostgreSQL can be run locally/in Docker for all developers. | Marri Sai Surekha |
| AS-04 | The team has access to a CRM sandbox or will mark CRM sync as planned-only for v1.0. | Mohamed Isharak M |
| AS-05 | Streamlit is acceptable as the delivery UI for evaluation purposes. | Maheksaba Akbar Shaikh |

---

## 12. User Workflows and End-to-End Use Cases

### UC-001 — Create and manage a prospect
- **Primary actor:** Sales Representative (UR-01)
- **Preconditions:** User is in the Leads UI.
- **Flow:** Add lead → enter details → system validates → duplicate check (FR-008) → save (FR-001/FR-009) → view in list (FR-002) → update or delete as needed (FR-003/FR-004) → move lifecycle stage (FR-005).
- **Postcondition:** Prospect persisted and visible; duplicates reported, not silently stored.
- **FRs:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, FR-009.

### UC-002 — Import leads from CSV
- **Primary actor:** Sales Representative
- **Flow:** Prepare CSV → upload → system parses → validates rows → detects duplicates → reports results → valid rows persisted (FR-007, FR-008, FR-009).
- **Exception:** Malformed file/rows produce a clear error and no partial silent data loss (partial-import behavior [TO BE CONFIRMED]).
- **FRs:** FR-007, FR-008, FR-009.

### UC-003 — Analyze a company and review intelligence
- **Primary actor:** Sales Representative
- **Flow:** Select/create lead → request analysis with company profile (FR-011) → AI service produces business needs (FR-012), opportunities (FR-013), industry insights (FR-014), qualification info (FR-015) → output validated (FR-018) → stored (FR-016) → displayed with the lead (FR-017).
- **Exception:** Provider failure shows an error state and allows retry (FR-018).
- **FRs:** FR-011 … FR-018.

### UC-004 — Generate and manage outreach
- **Primary actor:** Sales Representative
- **Flow:** Select lead → set tone/length/type/goal/pain points/industry (FR-020) → generate (FR-019) → review → refresh if unsatisfied (FR-021) → edit (FR-022) → copy (FR-023) → send [planned, D-05] (FR-024) → campaign stored (FR-025) and retrievable (FR-026).
- **FRs:** FR-019 … FR-027.

### UC-005 — Score a lead and act on the recommendation
- **Primary actor:** Sales Representative / Sales Manager
- **Flow:** Lead selected → system computes score (FR-028) and conversion probability (FR-029) from engagement/fit/intent/decision readiness (FR-030) → score stored (FR-031) → next-best-action shown with timing, channel, content strategy (FR-032) → displayed in UI (FR-033).
- **FRs:** FR-028 … FR-035.

### UC-006 — Capture and summarize a sales call
- **Primary actor:** Sales Representative
- **Flow:** Enter/open call notes (FR-044) → system summarizes (FR-036) → extracts discussion points (FR-037) and action items (FR-038) → interaction stored (FR-039) → reviewed in Conversations UI (FR-044).
- **FRs:** FR-036, FR-037, FR-038, FR-039, FR-044.

### UC-007 — Synchronize with CRM
- **Primary actor:** Sales Representative (planned)
- **Flow:** Configure field mapping (FR-040) → trigger contact/activity sync (FR-041) and deal-stage sync (FR-042) → outcome written to sync log (FR-043) → failure surfaced and logged (FR-045).
- **Status:** Planned; blocked by Decision D-06 (credentials/API access).
- **FRs:** FR-040 … FR-043, FR-045.

### UC-008 — Review sales KPIs
- **Primary actor:** Sales Manager (UR-02)
- **Flow:** Open dashboard → KPI cards show conversion rate, pipeline value, average response time, average sales cycle (FR-046 … FR-050) → values consistent with database (FR-053).
- **FRs:** FR-046 … FR-050, FR-053.

### UC-009 — Review pipeline and follow-ups
- **Primary actor:** Sales Manager / Sales Representative
- **Flow:** View Kanban pipeline (FR-051) → review follow-up recommendations panel (FR-052) → open recommended lead for action (links to FR-032 output).
- **FRs:** FR-051, FR-052, FR-032.

### UC-010 — End-to-end lead journey
- **Primary actor:** Sales Representative
- **Flow:** Import leads (UC-002) → analyze company (UC-003) → score lead (UC-005) → generate outreach (UC-004) → log call outcome (UC-006) → observe pipeline/KPI movement (UC-008).
- **Note:** This is the primary cross-module demonstration scenario for Milestone 4 UAT.
- **FRs:** all modules.

---

## 13. Module Acceptance Criteria

| AC ID | Module | Acceptance criterion |
|---|---|---|
| AC-001 | M1 | A user can create a prospect and find it again after an application restart. |
| AC-002 | M1 | A user can update and delete a prospect; deleted records no longer appear in the UI. |
| AC-003 | M1 | A valid CSV imports successfully; a CSV with duplicate entries reports duplicates rather than storing them twice. |
| AC-004 | M1 | Lifecycle stages can be assigned and changed, and the current stage is visible per lead. |
| AC-005 | M1 | Invalid input (missing required fields, malformed CSV) produces a clear error and no corrupt record. |
| AC-006 | M2 | Given a valid company profile, the system returns business needs, opportunities and industry insights in a structured, viewable form. |
| AC-007 | M2 | Intelligence is stored and displayed alongside its lead record after reload. |
| AC-008 | M2 | Lead qualification information is included in the intelligence output. |
| AC-009 | M2 | When the AI provider is unavailable, the user sees a clear error and existing data remains intact. |
| AC-010 | M2 | Output that fails validation is rejected, not stored. |
| AC-011 | M3 | Outreach can be generated for a selected lead using the six prompt inputs (tone, length, type, goal, pain points, industry). |
| AC-012 | M3 | Changing prompt inputs changes the generated output correspondingly. |
| AC-013 | M3 | Refresh produces a new variant; edit and copy work on the displayed content. |
| AC-014 | M3 | Outreach campaigns are stored and retrievable per lead. |
| AC-015 | M3 | The send action either functions per agreed design or is visibly marked as not available (D-05) — no misleading UI. |
| AC-016 | M4 | A score and conversion-probability estimate are produced for a lead with sufficient data, within the agreed scale (D-09). |
| AC-017 | M4 | Scores consider all four factors (engagement, fit, intent, decision readiness) per the agreed weighting. |
| AC-018 | M4 | Scores are stored and remain retrievable. |
| AC-019 | M4 | Recommendations include follow-up timing, channel and content strategy. |
| AC-020 | M4 | Scoring accuracy measured on the agreed test set meets the ≥ 85% target per the agreed metric (D-13). |
| AC-021 | M5 | Meeting/call notes produce a summary with key discussion points and action items. |
| AC-022 | M5 | Empty or invalid notes produce a clear message and no fabricated content. |
| AC-023 | M5 | Sales interactions are stored and listed in the Conversations UI. |
| AC-024 | M5 | CRM sync attempts, successes and failures are recorded in sync logs. *(Full sync execution depends on D-06.)* |
| AC-025 | M5 | A failed CRM sync does not delete or corrupt the local interaction record. |
| AC-026 | M6 | All four KPIs render on the dashboard with agreed definitions (D-10). |
| AC-027 | M6 | KPI values match values computed manually from the same database records. |
| AC-028 | M6 | The Kanban pipeline shows leads per lifecycle stage consistent with M1 stage data. |
| AC-029 | M6 | Follow-up recommendations panel shows recommendations derived from M4 output. |
| AC-030 | M6 | Dashboard renders without error when the database contains no records. |

---

## 14. Milestone-Based Acceptance Criteria

Aligned with the confirmed schedule (planned dates, not completion evidence):

| Milestone | Date | Acceptance criteria | Target |
|---|---|---|---|
| Milestone 1 | 20 October 2026 (Day 9) | AC-001 … AC-010 (M1+M2) demonstrated; deliverables present: requirements sign-off, API contracts, repository setup, database schema/migrations, UI wireframes, AI architecture, prospect CRUD, lead import, scoring/intelligence output, demo build, test report | ≥ 95% of records manageable; accurate intelligence outputs (accuracy definition pending, D-13) |
| Milestone 2 | 30 October 2026 (Day 19) | AC-011 … AC-020 (M3+M4) demonstrated, including outreach generation, scoring, validation/tuning, recommendations, strategy panel, QA report | ≥ 85% scoring accuracy (metric and dataset pending, D-13) |
| Milestone 3 | 10 November 2026 (Day 30) | AC-021 … AC-025 (M5) demonstrated with integration tests, conversations UI, demo and sign-off | Milestone sign-off; CRM sync scope depends on D-06 |
| Milestone 4 | 20 November 2026 (Day 40) | AC-026 … AC-030 (M6) plus full integration, performance tuning, RBAC checks, regression tests, UAT, deployment, documentation, final demonstration | ≥ 85% UAT satisfaction (survey pending, D-12); analysis/outreach < 5 s (conditions pending, D-11) |

---

## 15. Requirements Traceability Matrix (RTM)

Legend: Owner names are confirmed role assignments; test IDs reference `docs/test-plan.md`.

### 15.1 Functional requirements

| FR | Module | Owner (primary) | Support | Test cases |
|---|---|---|---|---|
| FR-001 | M1 | M Doran | Maheksaba Akbar Shaikh | TC-M1-001, TC-M1-002 |
| FR-002 | M1 | M Doran | Maheksaba Akbar Shaikh | TC-M1-003 |
| FR-003 | M1 | M Doran | Maheksaba Akbar Shaikh | TC-M1-004 |
| FR-004 | M1 | M Doran | Maheksaba Akbar Shaikh | TC-M1-005 |
| FR-005 | M1 | M Doran | Marri Sai Surekha | TC-M1-006 |
| FR-006 | M1 | M Doran | Maheksaba Akbar Shaikh | TC-M1-007 |
| FR-007 | M1 | M Doran | Marri Sai Surekha | TC-M1-008 |
| FR-008 | M1 | M Doran | Marri Sai Surekha | TC-M1-009 |
| FR-009 | M1 | Marri Sai Surekha | M Doran | TC-M1-010, TC-DB-001 |
| FR-010 | M1 | M Doran | Mahidhar Reddy | TC-E2E-001 |
| FR-011 | M2 | Mahidhar Reddy | M Doran [TO BE CONFIRMED D-07] | TC-M2-001, TC-M2-007 |
| FR-012 | M2 | Mahidhar Reddy | — | TC-M2-001 |
| FR-013 | M2 | Mahidhar Reddy | — | TC-M2-001 |
| FR-014 | M2 | Mahidhar Reddy | — | TC-M2-001 |
| FR-015 | M2 | Mahidhar Reddy | — | TC-M2-002 |
| FR-016 | M2 | Marri Sai Surekha | Mahidhar Reddy | TC-M2-003 |
| FR-017 | M2 | Maheksaba Akbar Shaikh | M Doran [TO BE CONFIRMED D-07] | TC-M2-004 |
| FR-018 | M2 | Mahidhar Reddy | Mohamed Isharak M | TC-M2-005, TC-M2-006 |
| FR-019 | M3 | Mahidhar Reddy | M Doran | TC-M3-001, TC-M3-008 |
| FR-020 | M3 | Mahidhar Reddy | Maheksaba Akbar Shaikh | TC-M3-002, TC-M3-003 |
| FR-021 | M3 | Mahidhar Reddy | — | TC-M3-004 |
| FR-022 | M3 | Maheksaba Akbar Shaikh | — | TC-M3-005 |
| FR-023 | M3 | Maheksaba Akbar Shaikh | — | TC-M3-006 |
| FR-024 | M3 | M Doran | Mohamed Isharak M | TC-M3-009 |
| FR-025 | M3 | Marri Sai Surekha | M Doran | TC-M3-007 |
| FR-026 | M3 | M Doran | Maheksaba Akbar Shaikh | TC-M3-007 |
| FR-027 | M3 | Maheksaba Akbar Shaikh | — | TC-M3-001, TC-M3-005 |
| FR-028 | M4 | Mahidhar Reddy | — | TC-M4-001 |
| FR-029 | M4 | Mahidhar Reddy | — | TC-M4-002 |
| FR-030 | M4 | Mahidhar Reddy | — | TC-M4-003 |
| FR-031 | M4 | Marri Sai Surekha | M Doran | TC-M4-004 |
| FR-032 | M4 | Mahidhar Reddy | Maheksaba Akbar Shaikh | TC-M4-005 |
| FR-033 | M4 | Maheksaba Akbar Shaikh | — | TC-M4-006 |
| FR-034 | M4 | Mohamed Isharak M | Mahidhar Reddy | TC-M4-008 |
| FR-035 | M4 | Mahidhar Reddy | — | TC-M4-007 |
| FR-036 | M5 | Mahidhar Reddy | M Doran [TO BE CONFIRMED D-07] | TC-M5-001, TC-M5-004 |
| FR-037 | M5 | Mahidhar Reddy | — | TC-M5-002 |
| FR-038 | M5 | Mahidhar Reddy | — | TC-M5-003 |
| FR-039 | M5 | Marri Sai Surekha | M Doran | TC-M5-005 |
| FR-040 | M5 | M Doran | Mohamed Isharak M | TC-M5-006 |
| FR-041 | M5 | M Doran | Mohamed Isharak M | TC-M5-007 |
| FR-042 | M5 | M Doran | Mohamed Isharak M | TC-M5-008 |
| FR-043 | M5 | Marri Sai Surekha | M Doran | TC-M5-009 |
| FR-044 | M5 | Maheksaba Akbar Shaikh | Mahidhar Reddy | TC-M5-001, TC-M5-005 |
| FR-045 | M5 | M Doran | Mohamed Isharak M | TC-M5-009, TC-API-005 |
| FR-046 | M6 | Maheksaba Akbar Shaikh | KPI computation API owner [TO BE CONFIRMED D-08] | TC-M6-001 |
| FR-047 | M6 | Maheksaba Akbar Shaikh | [TO BE CONFIRMED D-08] | TC-M6-002 |
| FR-048 | M6 | Maheksaba Akbar Shaikh | [TO BE CONFIRMED D-08] | TC-M6-003 |
| FR-049 | M6 | Maheksaba Akbar Shaikh | [TO BE CONFIRMED D-08] | TC-M6-004 |
| FR-050 | M6 | Maheksaba Akbar Shaikh | [TO BE CONFIRMED D-08] | TC-M6-001 … TC-M6-004 |
| FR-051 | M6 | Maheksaba Akbar Shaikh | M Doran [TO BE CONFIRMED D-08] | TC-M6-007 |
| FR-052 | M6 | Maheksaba Akbar Shaikh | Mahidhar Reddy | TC-M6-007 |
| FR-053 | M6 | Maheksaba Akbar Shaikh | Marri Sai Surekha | TC-M6-005, TC-M6-006 |

### 15.2 Non-functional requirements

| NFR | Test cases / verification |
|---|---|
| NFR-001 | TC-PERF-001, TC-PERF-002 |
| NFR-002 | TC-M2-005, TC-DB-004, TC-API-005 |
| NFR-003 | TC-E2E-003, UAT plan (Milestone 4) |
| NFR-004 | Architecture/code review checklist |
| NFR-005 | TC-SEC-001 … TC-SEC-004, TC-API-002 |
| NFR-006 | TC-SEC-001 |
| NFR-007 | RTM review at each milestone |
| NFR-008 | TC-DB-002, TC-DB-003, TC-M1-009 |
| NFR-009 | TC-PERF-001 |
| NFR-010 | TC-M5-009 |
| NFR-011 | TC-DEP-001, TC-DEP-002 |
| NFR-012 | Code review + log inspection checklist |

---

## 16. Risks, Dependencies and Unresolved Decisions

### 16.1 Requirements-level risks

| Risk ID | Risk | Impact on requirements |
|---|---|---|
| RR-01 | LLM provider inconsistency across documents (OpenAI/Groq/Gemini) | Affects FR-011 … FR-019, FR-028 … FR-036 delivery and testing |
| RR-02 | CRM credentials unavailable | FR-040 … FR-042 may remain planned-only at delivery |
| RR-03 | Email send provider unconfirmed | FR-024 may be descoped or UI-only |
| RR-04 | Acceptance targets (95%, 85%, <5 s) lack metric definitions | Sections 4 and 14 cannot be objectively evaluated |
| RR-05 | Navigation structure unresolved (D-03) | Affects UI requirements, UAT scripts and docs |
| RR-06 | Ownership gaps for Module 2 service layer and Module 6 analytics (D-07, D-08) | Risk of unowned FRs |
| RR-07 | Compressed schedule with milestone 1 already inside its delivery window | Requirements may be renegotiated under time pressure |

### 16.2 Decision register (requires team approval)

| Decision ID | Topic | Status | Options | Recommendation | Decision-maker |
|---|---|---|---|---|---|
| D-01 | LLM provider | Open | OpenAI / Groq / Gemini | Select one primary provider with an adapter layer for testability | Mahidhar Reddy + Mohamed Isharak M |
| D-02 | Database schema/table design (8-table claim unverified) | Open | 8-table plan / verified entity-driven schema | Approve entity-driven schema from `docs/database-design.md` | Marri Sai Surekha |
| D-03 | Navigation structure | Open | 4 tabs / 6 sidebar functions | Decide with the team before UAT scripts are finalized | Maheksaba Akbar Shaikh + Mohamed Isharak M |
| D-04 | Authentication/authorization design (JWT/RBAC) | Open | JWT+RBAC / simpler session / none for v1.0 | Confirm JWT+RBAC only if implementable in time; otherwise document a v1.0 decision | M Doran |
| D-05 | Email send integration | Open | Real provider / stubbed or disabled send | Ship with send disabled and clearly marked unless provider confirmed | M Doran + Mohamed Isharak M |
| D-06 | CRM (Salesforce/HubSpot) credentials & API access | Open | Sandbox access / planned-only | Confirm sandbox availability; else mark CRM sync as planned-only in v1.0 | Mohamed Isharak M |
| D-07 | Module 2 service/API-layer ownership | Open | Assign M Doran / other | Propose M Doran (backend) for M2 service layer | Mohamed Isharak M |
| D-08 | Module 6 analytics computation ownership | Open | Assign M Doran / frontend-computed | Propose backend KPI endpoints owned by M Doran; UI by Maheksaba | Mohamed Isharak M |
| D-09 | Lead score scale & probability format | Open | 0–100 / 1–5 / A–F | Propose 0–100 score and 0.00–1.00 probability | Mahidhar Reddy + Mohamed Isharak M |
| D-10 | KPI formulas (conversion rate, pipeline value, avg response time, avg sales cycle) | Open | Multiple formulas per metric | Approve one formula per KPI and document it in test plan | Mohamed Isharak M + Maheksaba Akbar Shaikh |
| D-11 | Performance measurement conditions (<5 s) | Open | Cold/warm start, provider latency excluded/included | Define: warm app, local DB, provider latency included/excluded stated | Mohamed Isharak M |
| D-12 | UAT satisfaction definition (≥85%) | Open | Survey scale and respondent set | Define survey questions and scoring before Milestone 4 | Mohamed Isharak M |
| D-13 | Scoring accuracy metric & test dataset (≥85%) | Open | Exact match / top-k / threshold band / LLM-judged | Approve metric, dataset size and denominator before Milestone 2 evaluation | Mohamed Isharak M + Mahidhar Reddy |
| D-14 | Deployment topology & CI/CD | Open | Docker Compose / manual run / CI pipeline | Confirm what "deployment" means for evaluation | Marri Sai Surekha |
| D-15 | Repository structure & implementation status | Open | — | Inspect repository and record actual state before publishing setup docs | Mohamed Isharak M |

---

## 17. Glossary

| Term | Definition |
|---|---|
| Prospect / Lead | A potential customer record managed in Module 1. |
| Lead lifecycle stage | The pipeline stage assigned to a lead (exact list [TO BE CONFIRMED]). |
| Intelligence output | AI-generated company analysis: business needs, opportunities, industry insights, qualification info (Module 2). |
| Outreach | AI-generated personalized sales message (Module 3). |
| Lead score | Numeric rating of a lead derived from engagement, fit, intent and decision readiness (Module 4). |
| Conversion probability | Estimated likelihood that a lead converts, expressed per Decision D-09. |
| Next-best-action | Recommended follow-up timing, channel and content strategy (Module 4). |
| Sales interaction | Stored record of a meeting/call with summary, discussion points and action items (Module 5). |
| CRM sync log | Record of a CRM synchronization attempt and its outcome (Module 5). |
| KPI | Key performance indicator shown on the dashboard (Module 6). |
| Kanban-style pipeline | Board visualization of leads by lifecycle stage (Module 6). |
| RTM | Requirements Traceability Matrix (Section 15). |
| UAT | User Acceptance Testing (Milestone 4). |
| LangGraph | Planned agent-orchestration library for AI workflows. |
| SQLAlchemy | Planned Python ORM for PostgreSQL access. |
| RBAC | Role-Based Access Control (proposed, Decision D-04). |

---

## Decisions Requiring Team Approval (summary)

1. **D-01** LLM provider (OpenAI vs Groq vs Gemini) — blocks AI testing consistency.
2. **D-02** Database schema — blocks final migrations.
3. **D-03** Navigation structure — blocks UAT scripts and UI docs.
4. **D-04** JWT/RBAC design — blocks security tests.
5. **D-05** Email send implementation — blocks FR-024 scope decision.
6. **D-06** CRM access — blocks FR-040 … FR-042 verification.
7. **D-07 / D-08** Module 2 and Module 6 API-layer ownership.
8. **D-09** Score scale and probability format.
9. **D-10** KPI formulas.
10. **D-11 / D-12 / D-13** Definitions for the performance, UAT and accuracy targets.
11. **D-14** Deployment meaning/topology.
12. **D-15** Repository structure and actual implementation status.

*End of SRS v1.0 — 22 October 2026.*
