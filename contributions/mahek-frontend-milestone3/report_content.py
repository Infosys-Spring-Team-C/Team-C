"""
report_content.py
Complete textual and data content for the Infosys Springboard Internship Technical Report
Project: Lead Management and Outreach Automation System (SalesGenie AI)
Student: Mahek Saba Shaikh | Role: Frontend Developer | Team: Team C
"""

METADATA = {
    "project_name": "Lead Management and Outreach Automation System",
    "project_code_name": "SalesGenie AI",
    "organization": "Infosys Springboard",
    "internship_program": "Technical Internship Program 2026",
    "team": "Team C",
    "role": "Frontend Developer",
    "student_name": "Mahek Saba Shaikh",
    "submission_date": "November 2026",
    "academic_year": "2026",
    "mentor_name": "Industry Mentor / Technical Lead",
    "college_name": "Department of Computer Science & Engineering"
}

# -----------------------------------------------------------------------------
# CHAPTER 1: COVER PAGE DATA
# -----------------------------------------------------------------------------
# Handled via docx cover formatting

# -----------------------------------------------------------------------------
# CHAPTER 2: CERTIFICATE PAGE TEXT
# -----------------------------------------------------------------------------
CERTIFICATE_TEXT = """
This is to certify that the project report entitled "Lead Management and Outreach Automation System" (SalesGenie AI) submitted by Mahek Saba Shaikh (Team C) in partial fulfillment of the requirements for the Infosys Springboard Technical Internship Program 2026 is an authentic record of the frontend engineering work carried out by her under our guidance and supervision.

To the best of our knowledge, the matter embodied in this report represents genuine frontend software engineering contributions, UI component implementation, API integration, and automated user-interface validation, and has not been submitted elsewhere for the award of any degree or diploma.
"""

# -----------------------------------------------------------------------------
# CHAPTER 3: ACKNOWLEDGEMENT
# -----------------------------------------------------------------------------
ACKNOWLEDGEMENT_TEXT = """
I would like to express my profound gratitude to Infosys Springboard for providing me with this exceptional internship opportunity. Working on an enterprise-grade AI system has been an invaluable stepping stone in my career as a software engineer.

I extend my heartfelt thanks to our industry mentors and project coordinators at Infosys Springboard for their continuous guidance, technical insights, and constructive feedback throughout the project lifecycle. Their rigorous architectural benchmarks and industry best practices inspired me to push the boundaries of responsive frontend engineering, state persistence, and accessible design systems.

I also express my sincere appreciation to my esteemed colleagues in Team C. Their seamless collaboration, prompt API contract alignment, and robust backend engineering enabled a highly effective pairing environment between the frontend presentation layer and the FastAPI intelligence backend.

Finally, I am deeply grateful to my academic institution, professors, and family for their unwavering encouragement, patience, and support throughout the duration of this internship.
"""

# -----------------------------------------------------------------------------
# CHAPTER 4: ABSTRACT
# -----------------------------------------------------------------------------
ABSTRACT_TEXT = """
Modern B2B enterprise sales cycles are heavily constrained by manual account prospecting, fragmented contact records, slow qualification cadences, and impersonal, generic cold outreach that consistently fails to engage decision-makers. The "Lead Management and Outreach Automation System" (internally dubbed SalesGenie AI) was conceived and engineered under the Infosys Springboard Technical Internship Program to eliminate these operational bottlenecks by unifying autonomous prospect discovery, multi-factor AI lead scoring, strategic intelligence profiling, and personalized communication generation within an intuitive, single-pane application.

This technical report documents the complete frontend engineering and architectural implementation delivered by Mahek Saba Shaikh in the designated role of Frontend Developer within Team C. The frontend presentation layer was designed and developed utilizing Python 3.11 and the Streamlit 1.66 framework, fortified by a custom-engineered CSS3 design system featuring dynamic runtime theming, glassmorphic containerization, responsive tabular layouts, and tactile interactive controls. The user interface is cleanly segregated into four operational workflows: (1) Leads Management, providing dual-mode manual entry with comprehensive client-side schema validation alongside high-throughput CSV batch ingestion powered by Pandas; (2) Lead Intelligence & Qualification Engine, presenting AI-synthesized company pain points, strategic opportunities, and real-time conversion probability metrics; (3) Outreach Studio, featuring a Superhuman-style email drafting suite with dynamic tone modulation, live word/character/read-time telemetry, and truthful delivery status verification; and (4) Executive Dashboard, offering live pipeline KPI metric cards, qualification status distribution charts, and a dynamic prospect leaderboard.

The frontend seamlessly connects to a high-performance FastAPI RESTful service across ten dedicated API endpoints, enforcing robust exception handling, connection timeout resilience, and offline visual feedback indicators. Comprehensive automated testing was executed via Python's unittest framework (10 out of 10 integration test cases passed in 0.26 seconds) and verified through automated headless browser execution using Selenium WebDriver. The resulting implementation delivers a highly polished, enterprise-ready user experience that accelerates prospect processing while maintaining absolute technical truthfulness and architectural rigor.
"""

# -----------------------------------------------------------------------------
# CHAPTER 6: INTRODUCTION TO INFOSYS SPRINGBOARD INTERNSHIP
# -----------------------------------------------------------------------------
CHAPTER_6_TEXT = """
### 6.1 The Infosys Springboard Initiative
Infosys Springboard is a flagship digital skilling and competency-building initiative launched by Infosys to empower student engineers and aspiring technologists across emerging disciplines including Artificial Intelligence, Cloud Computing, Full-Stack Software Engineering, and Enterprise Product Development. Designed to bridge the critical gap between academic curriculum and contemporary industry expectations, the Springboard ecosystem combines curated technical learning pathways, hands-on masterclasses, and intensive project-based technical internships.

The internship program operates under an industry-simulated Agile software development life cycle (SDLC). Interns are organized into cross-functional engineering teams, assigned distinct engineering roles, and tasked with building production-grade solutions to real-world enterprise challenges.

### 6.2 Team-Based Collaborative Structure (Team C)
Within the framework of the internship, students were organized into collaborative engineering squads. As part of **Team C**, engineering responsibilities were distributed across dedicated roles to reflect real-world enterprise practices:
- **Frontend Development:** Responsible for user experience (UI/UX) conceptualization, interactive client architecture, client-side data validation, dynamic design systems, state caching, and RESTful API consumption.
- **Backend & Database Engineering:** Responsible for relational schema architecture (SQLAlchemy ORM, SQLite/PostgreSQL), FastAPI microservices, and CRUD persistence pipelines.
- **AI & Intelligence Engineering:** Responsible for Large Language Model (LLM) orchestration, prompt engineering, heuristic scoring rules, and natural language generation algorithms.
- **DevOps & Integration:** Responsible for environment management, configuration hardening, and service orchestration.

### 6.3 Objectives and Pedagogical Framework
The primary pedagogical objectives of the internship included:
1. **Practical Agile Execution:** Participating in milestone-driven development sprints spanning requirements elicitation, architectural wireframing, component implementation, API integration, and user-acceptance testing.
2. **Enterprise Architectural Standards:** Upholding clean coding standards, robust error handling, truthful visual reporting, and complete separation of concerns.
3. **Role-Specific Accountability:** Demonstrating clear ownership of assigned frontend responsibilities while actively coordinating API contracts with backend collaborators.
"""

# -----------------------------------------------------------------------------
# CHAPTER 7: PROJECT OVERVIEW
# -----------------------------------------------------------------------------
CHAPTER_7_TEXT = """
### 7.1 Vision and Mission of SalesGenie AI
The **Lead Management and Outreach Automation System** (branded as **SalesGenie AI**) was developed to transform modern B2B sales development. Traditional sales representatives spend over 65% of their daily working hours conducting manual web research on prospect accounts, cross-referencing industry databases, drafting redundant follow-up emails, and logging notes across disconnected spreadsheets and CRMs. This operational friction delays outreach, introduces human error, and severely degrades pipeline velocity.

SalesGenie AI automates this operational lifecycle through an integrated, intelligent copilot interface. By combining automated firmographic data capture, deep LLM-driven company profiling, deterministic conversion qualification, and personalized communication authoring, the platform empowers sales reps to prioritize high-value deals and engage enterprise buyers with hyper-relevant messaging in seconds.

### 7.2 End-to-End Prospect Journey
The platform orchestrates a continuous, five-stage prospect acceleration lifecycle:
1. **Prospect Ingestion:** Accounts are ingested either individually via an intuitive, validated multi-field entry form or in bulk via a validated CSV dataset parser.
2. **Autonomous Account Profiling:** The platform extracts the prospect's company size, funding stage, industry vertical, and stated operational pain points, querying the AI intelligence engine to synthesize business needs, high-value opportunities, and industry trends.
3. **Multi-Factor Qualification Scoring:** The system evaluates the lead across four core heuristic dimensions (Funding Stage, Company Size, Industry Fit, and Need Urgency), computing an objective qualification score (0–100) and mapping it to distinct urgency tiers (Very Hot, Hot, Warm, Cold).
4. **Tailored Outreach Generation:** Using prospect firmographics and intelligence signals, the platform drafts a personalized cold email tailored to specific emotional tones (Professional, Friendly, Urgent).
5. **Executive Visibility & Pipeline Governance:** Sales managers monitor total pipeline volume, qualification distributions, conversion rates, and ranked leaderboards through live interactive visualizations.
"""

# -----------------------------------------------------------------------------
# CHAPTER 8: PROBLEM STATEMENT
# -----------------------------------------------------------------------------
CHAPTER_8_TEXT = """
### 8.1 The Enterprise Sales Dilemma
In competitive B2B software sales, timing and relevance dictate deal outcomes. Despite rapid advancements in enterprise software, sales development teams continue to face substantial operational hurdles:

1. **Labor-Intensive Account Research:** Sales development representatives (SDRs) spend an average of 45 to 60 minutes researching a single target account before sending an initial cold email. Understanding a company's funding history, technical stack, recent organizational changes, and pain points requires querying multiple disparate sources (LinkedIn, Crunchbase, press releases, company websites).
2. **Low-Performing Generic Outreach:** When SDRs attempt to scale manual prospecting, they inevitably resort to generic email templates. Mass email campaigns without personalized context yield dismal response rates (typically below 2%), burn company domain reputation, and alienate key decision-makers.
3. **Subjective and Inconsistent Lead Qualification:** Without a standardized, data-backed qualification framework, sales reps prioritize leads based on subjective intuition rather than empirical conversion indicators. High-intent enterprise prospects slip through the cracks, while low-budget accounts consume valuable sales capacity.
4. **Tool Fragmentation and Context Switching:** Sales teams frequently juggle disparate software tools: a spreadsheet for prospect lists, a standalone CRM for pipeline tracking, an AI text playground for drafting emails, and separate email clients for dispatch. Switching between disconnected windows destroys workflow focus and introduces data drift.
5. **Lack of Truthful Transparency in Automation:** Many automation tools report misleading dispatch confirmations or obscure delivery failures when underlying communication transports (such as SMTP relays) are unconfigured, undermining user trust.

### 8.2 Scope of the Frontend Solution
The frontend developer's mandate was to resolve these pain points by building a unified, highly responsive single-page application (SPA) interface. The frontend had to encapsulate prospect ingestion, intelligence analysis, scoring visualization, and email composition into a seamless, distraction-free environment that maximizes sales rep productivity and enforces strict data validity.
"""

# -----------------------------------------------------------------------------
# CHAPTER 9: PROJECT OBJECTIVES
# -----------------------------------------------------------------------------
CHAPTER_9_TEXT = """
The primary engineering objectives established for the frontend development of SalesGenie AI were:

1. **Unified Single-Pane User Experience:** Consolidate lead directory management, AI profiling, lead qualification scoring, personalized email drafting, and executive pipeline analytics into a single responsive Streamlit dashboard.
2. **Tactile, Luxury Design System:** Develop an enterprise-grade visual presentation layer utilizing custom CSS3 variables, glassmorphic card styling, typography hierarchies (`Outfit` and `Plus Jakarta Sans`), glowing hover states, and dynamic status badges.
3. **Dynamic Multi-Theme Engine:** Implement a runtime theme switcher allowing users to toggle between four bespoke color palettes (Cyber Indigo, Emerald Luxe, Cosmic Violet, and Oceanic Sapphire) without disrupting active session state.
4. **Dual-Mode Data Ingestion Interface:** Provide an accessible manual lead creation form with strict client-side validation rules alongside a high-throughput CSV bulk ingestion tool with downloadable schema templates and live Pandas previews.
5. **Interactive Intelligence & Scoring Visualization:** Create visually striking presentation components for AI company analysis and lead qualification scores, utilizing color-coded urgency badges, conversion percentages, and expandable factor attribution accordions.
6. **Superhuman-Style Email Studio:** Build an email authoring suite featuring tone-of-voice selectors, live word count, character count, and reading time telemetry, one-click clipboard copying, and honest SMTP delivery status reporting.
7. **Robust RESTful API Integration:** Establish a resilient HTTP communication layer connecting the Streamlit frontend to the FastAPI backend with comprehensive error handling, graceful offline fallbacks, and connection status indicators.
8. **Automated Verification and Testing:** Validate all UI integration points and client-server interactions through automated test suites and headless browser automation.
"""

# -----------------------------------------------------------------------------
# CHAPTER 10: TECHNOLOGIES AND TOOLS USED
# -----------------------------------------------------------------------------
CHAPTER_10_TEXT = """
### 10.1 Core Frontend Technologies
- **Python 3.11.9:** The primary programming language utilized for both the application logic and presentation scripting. Python 3.11 provides significant performance improvements, enhanced tracebacks, and native type hinting support.
- **Streamlit 1.66.1:** An advanced, open-source Python framework for building interactive, data-driven web applications. Streamlit was selected for its rapid prototyping capabilities, native session state management, seamless data frame rendering, and modular tab architecture.
- **Pandas 3.1.0:** High-performance data manipulation and analysis library utilized on the frontend for tabular parsing, CSV dataset ingestion, dynamic column filtering, and DataFrame visualization.
- **Requests 2.34.2:** A battle-tested, synchronous HTTP library used to formulate RESTful client calls (`GET`, `POST`) from the Streamlit frontend to the FastAPI backend endpoints.
- **Custom CSS3 & HTML5 Injection:** Pure CSS styling injected directly into the Streamlit DOM via `st.markdown(..., unsafe_allow_html=True)`. Incorporates CSS custom properties (`:root` variables), modern flexbox and grid layouts, glassmorphism (`backdrop-filter: blur(14px)`), box-shadow glows, and tactile button transitions.
- **Google Fonts Typography:** Web fonts dynamically imported via Google Fonts CDN:
  - *Outfit:* Utilized for display headers, numeric KPI metrics, and high-impact badges.
  - *Plus Jakarta Sans:* Utilized for body prose, tabular typography, and form input controls.

### 10.2 Backend & Service Architecture (Consumed via REST)
- **FastAPI 0.162.0:** High-performance asynchronous web framework hosting the backend API endpoints consumed by the frontend.
- **Uvicorn 0.54.0:** ASGI server running the FastAPI backend on `http://127.0.0.1:8000`.
- **SQLAlchemy 2.1.6 ORM & SQLite Database:** Relational database layer queried by the backend and visualized on the frontend.
- **Pydantic 2.14.1:** Data validation and schema definition library governing client-server JSON payloads.

### 10.3 Testing & Verification Tooling
- **Unittest:** Python's standard automated unit and integration testing framework.
- **Selenium WebDriver 4.52.0 & Chrome Headless:** Automated browser orchestration framework used to drive the running Streamlit web application, trigger tab transitions, interact with UI buttons, and capture full-resolution screenshots.
- **Visual Studio Code:** Primary integrated development environment (IDE) utilized for coding, debugging, and terminal execution.
"""

# -----------------------------------------------------------------------------
# CHAPTER 11: FRONTEND ARCHITECTURE AND PROJECT STRUCTURE
# -----------------------------------------------------------------------------
CHAPTER_11_TEXT = """
### 11.1 Frontend Architectural Paradigm
The frontend architecture of SalesGenie AI follows a stateful, event-driven Single-Page Application (SPA) model implemented entirely in Python using Streamlit. Unlike traditional React or Angular SPAs that require node compilation, complex bundlers, and separate client-server repositories, Streamlit executes the Python script sequentially on user interaction while preserving persistent state across rerun cycles via `st.session_state`.

The architecture comprises four distinct logical layers:
1. **Design System & Theme Engine:** Defines CSS tokens, color palettes, and global typography injected at the top of the execution cycle.
2. **State Management & Caching Layer:** Initializes and synchronizes global session keys (`backend_url`, `selected_lead_id`, `leads_cache`, `insights_cache`, `scores_cache`, `email_subject`, `email_body`).
3. **RESTful API Service Client:** Encapsulates network communication into reusable helper functions (`api_get`, `api_post`) with automated URL formatting, error handling, and connection timeout safeguards.
4. **Presentation & Layout Layer:** Organizes the user interface into a fixed sidebar, an executive hero header, and four segmented operational tabs (`Leads Management`, `Lead Intelligence & Scoring`, `Outreach Studio`, and `Executive Dashboard`).

### 11.2 Project Directory Structure
```
Infosys/
│
├── app.py                         # Complete Streamlit Frontend Application (1,480 lines)
├── main.py                        # FastAPI Backend REST API Server (315 lines)
├── run_all.py                     # Full-Stack Multi-Process Orchestrator
├── requirements.txt               # Python Package Dependencies
├── sample_leads.csv               # Seed / Sample CSV Dataset for Batch Ingestion
├── salesgenie.db                  # SQLite Relational Database File
│
├── .streamlit/
│   └── config.toml                # Streamlit Server & Theme Configuration
│
├── .vscode/
│   └── launch.json                # VS Code Multi-Service Debugger Profiles
│
├── database/
│   ├── __init__.py                # Database Package Initializer
│   ├── connection.py              # SQLAlchemy Engine, SessionLocal, Base Config
│   └── models.py                  # Relational ORM Models (Lead, LeadScore, Insight, etc.)
│
├── modules/
│   ├── __init__.py                # Modules Package Initializer
│   ├── module1_leads.py           # Lead Management Business Logic & CRUD
│   ├── module2_intelligence.py    # Company Profiling & AI Intelligence Service
│   ├── module3_outreach.py        # Email Generation & Outreach Strategy Engine
│   ├── module4_scoring.py         # Multi-Factor Heuristic Lead Scoring Model
│   ├── module5_conversation.py    # Sales Call Transcript Summarizer
│   └── module6_dashboard.py       # Executive Dashboard Metrics & Aggregations
│
├── tests/
│   ├── __init__.py                # Test Package Initializer
│   └── test_frontend_and_api.py   # Full-Stack Integration & API Validation Suite
│
└── Internship_Report/
    ├── INTERNSHIP_TECHNICAL_REPORT.md  # Complete Markdown Technical Report Source
    ├── Internship_Technical_Report_Mahek_Saba_Shaikh.docx  # Final Formatted Word Report
    └── screenshots/
        ├── fig1_main_dashboard.png       # Executive Dashboard Top View
        ├── fig1b_dashboard_analytics.png # Executive Analytics Charts & Leaderboard
        ├── fig2_leads_management.png     # Manual Prospect Capture Form
        ├── fig2b_leads_directory.png     # Active Prospects Directory Table
        ├── fig3_lead_intelligence.png    # Strategic AI Company Profiling Cards
        ├── fig4_lead_scoring.png         # Lead Qualification Hero & Factor Attribution
        ├── fig5_outreach_studio.png      # Outreach Studio Guidance & Tone Controls
        └── fig6_ai_email_generator.png   # Superhuman Email Studio & Live Editor
```
"""

# -----------------------------------------------------------------------------
# CHAPTER 12: MY ROLE AND RESPONSIBILITIES
# -----------------------------------------------------------------------------
CHAPTER_12_TEXT = """
### 12.1 Specific Ownership as Frontend Developer
As the designated **Frontend Developer** for **Team C**, my primary mandate was to conceptualize, design, implement, and validate the entire client-facing presentation layer of the SalesGenie AI platform. All work documented in this report represents my direct individual contributions to the frontend software engineering lifecycle.

My core responsibilities encompassed:
1. **User Experience (UI/UX) Design:** Wireframing intuitive, multi-stage sales workflows that eliminate clutter, minimize cognitive overhead, and provide continuous visual feedback to sales reps.
2. **Custom CSS Design System Engineering:** Developing a bespoke, luxury glassmorphic styling system using CSS3 custom properties, responsive flexbox/grid containers, tactile glowing buttons, and dynamic status badges without relying on external UI component libraries.
3. **Multi-Theme Engine Implementation:** Designing and integrating four runtime theme palettes (Cyber Indigo, Emerald Luxe, Cosmic Violet, Oceanic Sapphire) allowing users to customize dashboard aesthetics dynamically.
4. **Interactive Form Design & Validation:** Constructing responsive input forms equipped with client-side data validation rules that prevent empty submissions, malformed email addresses, and truncated company names.
5. **CSV Dataset Bulk Ingestion UX:** Implementing a drag-and-drop file ingestion module featuring automated CSV parsing, live schema previewing via Pandas DataFrames, and downloadable template generation.
6. **State Management & Client-Side Caching:** Implementing resilient session state management (`st.session_state`) across tab transitions, ensuring that prospect selections, scoring results, and email drafts persist without unexpected re-initialization.
7. **RESTful API Client Integration:** Architecting reusable API communication functions (`api_get`, `api_post`) that handle HTTP status codes, connection errors, request timeouts, and server offline states gracefully.
8. **Automated Testing & Quality Assurance:** Collaborating on end-to-end integration tests (`tests/test_frontend_and_api.py`) and executing browser-level automated validation via Selenium WebDriver to guarantee responsive rendering and zero runtime exceptions.

### 12.2 Demarcation of Work (What Was NOT My Contribution)
In adherence to academic integrity and project reporting guidelines, the following areas were engineered by my esteemed collaborators in Team C and are explicitly recognized as **team contributions** rather than my personal deliverables:
- **Backend API Implementation:** Development of the underlying FastAPI routes, Pydantic schema declarations, and Uvicorn server configuration (`main.py`) was handled by backend teammates.
- **Database Architecture & ORM:** Database connection pooling, SQLite file configuration, and SQLAlchemy relational model definitions (`database/connection.py`, `database/models.py`) were implemented by database teammates.
- **AI Model Prompting & Heuristics:** The backend OpenAI prompt engineering, heuristic scoring calculation logic, and meeting transcript processing (`modules/module2_intelligence.py`, `modules/module4_scoring.py`, `modules/module5_conversation.py`) were authored by AI engineering teammates.
- **DevOps & Infrastructure:** Database migration scripts and deployment container configurations were managed by DevOps teammates.

My contribution was strictly centered on the **frontend consumer layer**: translating these underlying backend services into a seamless, visual, and highly functional human-computer interface.
"""

print("report_content.py initialized successfully!")

