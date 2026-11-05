"""SalesGenie AI - Streamlit client.

Presentation layer only.  Every read and write goes through
``frontend/api_compat.py`` to the FastAPI backend; this file never touches the
database, holds provider keys, or invents data.

Design: warm peach-and-cream system in ``frontend/theme.py``.
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

_FRONTEND_DIR = str(Path(__file__).resolve().parent)
if _FRONTEND_DIR not in sys.path:
    sys.path.insert(0, _FRONTEND_DIR)

import api_compat  # noqa: E402
import theme  # noqa: E402
from theme import esc  # noqa: E402

# ---------------------------------------------------------------------------
# Page configuration and design system
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SalesGenie AI - Sales Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(theme.css(), unsafe_allow_html=True)

NAV = [
    ("overview", "Overview", ":material/dashboard:"),
    ("leads", "Leads", ":material/groups:"),
    ("intelligence", "Lead Intelligence", ":material/psychology:"),
    ("outreach", "Outreach Studio", ":material/edit_note:"),
    ("conversations", "Conversations", ":material/forum:"),
    ("analytics", "Analytics", ":material/monitoring:"),
]

STAGE_LABELS = {
    "prospecting": "Prospecting",
    "discovery": "Discovery",
    "qualified": "Qualified",
    "proposal": "Proposal",
    "negotiation": "Negotiation",
    "converted": "Converted",
    "lost": "Lost",
}


def _backend_url() -> str:
    try:
        if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
            return str(st.secrets["BACKEND_URL"]).strip().rstrip("/")
    except Exception:  # noqa: BLE001 - secrets file is optional
        pass
    return api_compat.resolve_base_url()


DEFAULTS = {
    "nav": "overview",
    "backend_url": _backend_url(),
    "selected_lead_id": None,
    "email_subject": "",
    "email_body": "",
    "email_tone": "professional",
    "leads_cache": [],
    "insights_cache": {},
    "scores_cache": {},
    "conversations_cache": {},
    "recommendation_cache": {},
    "draft_checked": {},
    "draft_lead_id": None,
    "signed_out": False,
}
for _key, _value in DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value.copy() if isinstance(_value, (list, dict)) else _value


# ---------------------------------------------------------------------------
# API helpers and short-lived caches
# ---------------------------------------------------------------------------
def api_get(endpoint: str, params: dict | None = None, timeout: float = 8.0):
    return api_compat.api_get(
        st.session_state.backend_url, endpoint, params=params, timeout=timeout
    )


def api_post(endpoint: str, json_data: dict | None = None, timeout: float = 30.0):
    return api_compat.api_post(
        st.session_state.backend_url, endpoint, json_data=json_data, timeout=timeout
    )


def _fresh(stamp_key: str, ttl: float) -> bool:
    stamp = st.session_state.get(stamp_key)
    return stamp is not None and (time.time() - stamp) < ttl


def load_health(force: bool = False) -> tuple[bool, dict]:
    if not force and _fresh("_health_at", 15):
        return st.session_state.get("_health", (False, {}))
    ok, data = api_get("/health", timeout=3)
    payload = data if isinstance(data, dict) else {}
    st.session_state["_health"] = (ok, payload)
    st.session_state["_health_at"] = time.time()
    return ok, payload


def load_leads(force: bool = False) -> list[dict]:
    if not force and _fresh("_leads_at", 20) and st.session_state.leads_cache:
        return st.session_state.leads_cache
    ok, data = api_get("/leads/", timeout=8)
    if ok and isinstance(data, list):
        st.session_state.leads_cache = data
        st.session_state["_leads_at"] = time.time()
        st.session_state["_leads_error"] = None
    else:
        st.session_state["_leads_error"] = (
            (data or {}).get("error") if isinstance(data, dict) else "Unable to load leads."
        )
    return st.session_state.leads_cache


def load_analytics(force: bool = False) -> tuple[bool, dict]:
    if not force and _fresh("_analytics_at", 20):
        return st.session_state.get("_analytics", (False, {}))
    ok, data = api_get("/analytics/dashboard", timeout=12)
    result = (ok, data if isinstance(data, dict) else {})
    st.session_state["_analytics"] = result
    st.session_state["_analytics_at"] = time.time()
    return result


def load_follow_ups(force: bool = False) -> list[dict]:
    if not force and _fresh("_followups_at", 20):
        return st.session_state.get("_followups", [])
    ok, data = api_get("/follow-ups", timeout=8)
    rows = data if ok and isinstance(data, list) else []
    st.session_state["_followups"] = rows
    st.session_state["_followups_at"] = time.time()
    return rows


def load_score(lead_id):
    cache = st.session_state.scores_cache
    if lead_id in cache:
        return cache[lead_id]
    ok, data = api_get(f"/intelligence/score/{lead_id}", timeout=10)
    cache[lead_id] = data if ok else None
    return cache[lead_id]


def load_insight(lead_id):
    cache = st.session_state.insights_cache
    if lead_id in cache:
        return cache[lead_id]
    ok, data = api_get(f"/intelligence/analyze/{lead_id}", timeout=10)
    cache[lead_id] = data if ok else None
    return cache[lead_id]


def current_user():
    if "user" in st.session_state:
        return st.session_state["user"]
    ok, data = api_get("/auth/me", timeout=4)
    st.session_state["user"] = data if ok and isinstance(data, dict) else None
    return st.session_state["user"]


def go(page: str, lead_id=None) -> None:
    st.session_state.nav = page
    if lead_id is not None:
        st.session_state.selected_lead_id = lead_id
    st.rerun()


# ---------------------------------------------------------------------------
# Small formatting helpers
# ---------------------------------------------------------------------------
def para(value) -> str:
    return esc(value).replace("\n", "<br>")


def when(value) -> str:
    if not value:
        return "-"
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.strftime("%d %b %Y, %H:%M")
    except ValueError:
        return str(value)[:19]


def band_for(score) -> tuple[str, str]:
    try:
        value = int(score)
    except (TypeError, ValueError):
        return "Unscored", "muted"
    if value >= 70:
        return "Qualified", "success"
    if value >= 45:
        return "Nurture", "warning"
    return "Low priority", "muted"


def lead_label(lead: dict) -> str:
    return f"#{lead.get('lead_id')} - {lead.get('company_name') or 'Untitled'}"


def lead_options(leads: list[dict]) -> dict:
    return {lead["lead_id"]: lead_label(lead) for lead in leads if lead.get("lead_id")}


def pick_lead(leads: list[dict], key: str, label: str = "Prospect"):
    options = lead_options(leads)
    if not options:
        return None
    ids = list(options.keys())
    current = st.session_state.selected_lead_id
    index = ids.index(current) if current in ids else 0
    chosen = st.selectbox(
        label, ids, index=index, format_func=lambda value: options[value], key=key
    )
    st.session_state.selected_lead_id = chosen
    return next((lead for lead in leads if lead["lead_id"] == chosen), None)


def bullet_list(values) -> str:
    items = [str(value).strip() for value in values or [] if str(value).strip()]
    if not items:
        return '<span class="sg-muted">None recorded.</span>'
    return "<ul style='margin:0.2rem 0 0 1.1rem;padding:0;font-size:0.87rem;line-height:1.7;'>" + "".join(
        f"<li>{esc(item)}</li>" for item in items
    ) + "</ul>"


def status_badge(priority: str) -> str:
    mapping = {"hot": "success", "warm": "warning", "cold": "muted"}
    label = (priority or "unscored").capitalize()
    return theme.badge(label, mapping.get((priority or "").lower(), "muted"))


def top_status(health_ok: bool, payload: dict) -> str:
    engine = str(payload.get("ai_backend") or "heuristic").replace("_", " ").title()
    if health_ok:
        return (
            '<div class="sg-card-cream" style="text-align:right;">'
            + theme.status_dot("Backend online", "success")
            + f'<div class="sg-muted" style="margin-top:4px;">Scoring engine: {esc(engine)}</div>'
            + "</div>"
        )
    return (
        '<div class="sg-card-cream" style="text-align:right;">'
        + theme.status_dot("Backend offline", "error")
        + '<div class="sg-muted" style="margin-top:4px;">Actions are disabled until it reconnects</div>'
        + "</div>"
    )


def header(eyebrow: str, title: str, description: str, health_ok: bool, payload: dict) -> None:
    left, right = st.columns([3, 1.1], gap="large")
    with left:
        theme.page_head(eyebrow, title, description)
    with right:
        st.markdown(top_status(health_ok, payload), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Authentication gate
# ---------------------------------------------------------------------------
def render_login() -> None:
    _, middle, _ = st.columns([1, 1.15, 1])
    with middle:
        st.markdown(theme.brand(), unsafe_allow_html=True)
        st.markdown(
            '<div class="sg-card" style="margin-top:1rem;">'
            '<div class="sg-eyebrow">Sign in</div>'
            '<div style="font-size:1.35rem;font-weight:700;margin-bottom:0.2rem;">'
            "Welcome back</div>"
            '<div class="sg-muted" style="margin-bottom:1rem;">'
            "Use your SalesGenie account. Credentials are exchanged for a token and never stored."
            "</div></div>",
            unsafe_allow_html=True,
        )
        with st.form("signin"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submitted:
            ok, message = api_compat.login(
                st.session_state.backend_url, email.strip(), password
            )
            if ok:
                st.session_state.signed_out = False
                st.session_state.pop("user", None)
                for key in ("leads_cache", "insights_cache", "scores_cache"):
                    st.session_state[key] = [] if key == "leads_cache" else {}
                st.rerun()
            else:
                theme.error_note(message)
        st.caption(
            "Local demos can also start the API with AUTH_ENABLED=false; "
            "the app then opens without a sign-in."
        )


if st.session_state.signed_out:
    render_login()
    st.stop()

health_ok, health_payload = load_health()
user = current_user() if health_ok else None

# ---------------------------------------------------------------------------
# Sidebar: brand, navigation, active prospect, connection, account
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(theme.brand(), unsafe_allow_html=True)
    st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)

    for key, label, icon in NAV:
        if st.button(
            label,
            key=f"nav_{key}",
            icon=icon,
            width="stretch",
            type="primary" if st.session_state.nav == key else "secondary",
        ):
            st.session_state.nav = key
            st.rerun()

    st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)

    leads = load_leads()
    st.markdown('<div class="sg-kpi-label">Active prospect</div>', unsafe_allow_html=True)
    if leads:
        options = lead_options(leads)
        ids = list(options.keys())
        current = st.session_state.selected_lead_id
        index = ids.index(current) if current in ids else 0
        chosen = st.selectbox(
            "Active prospect",
            ids,
            index=index,
            format_func=lambda value: options[value],
            label_visibility="collapsed",
        )
        st.session_state.selected_lead_id = chosen
        active = next((lead for lead in leads if lead["lead_id"] == chosen), None)
        if active:
            st.markdown(
                f'<div class="sg-muted" style="margin-top:2px;">'
                f'{esc(active.get("contact_name") or "No contact")} · '
                f'{esc(active.get("industry") or "No industry")}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="sg-muted">No prospects yet.</div>', unsafe_allow_html=True)

    if st.button("Refresh data", icon=":material/refresh:", width="stretch"):
        load_leads(force=True)
        load_health(force=True)
        load_analytics(force=True)
        load_follow_ups(force=True)
        st.session_state["_leads_at"] = time.time()
        st.toast("Data refreshed.")
        st.rerun()

    st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)

    if health_ok:
        st.markdown(theme.status_dot("Backend connected", "success"), unsafe_allow_html=True)
    else:
        st.markdown(theme.status_dot("Backend offline", "error"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="sg-muted" style="margin-top:4px;">'
        f'{esc(st.session_state.backend_url)}</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Connection", expanded=False):
        backend_input = st.text_input(
            "API base URL",
            value=st.session_state.backend_url,
            help="Base URL of the FastAPI service, for example http://127.0.0.1:8000",
        )
        if backend_input.strip().rstrip("/") != st.session_state.backend_url:
            if st.button("Apply URL", width="stretch"):
                st.session_state.backend_url = backend_input.strip().rstrip("/")
                st.session_state.pop("_health_at", None)
                st.rerun()

    st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)

    if user:
        st.markdown(
            f'<div style="font-size:0.86rem;font-weight:650;">{esc(user.get("full_name") or user.get("email"))}</div>'
            f'<div class="sg-muted">{esc(user.get("role", ""))} · {esc(user.get("email", ""))}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="sg-muted">Local session</div>', unsafe_allow_html=True)

    if st.button("Sign out", icon=":material/logout:", width="stretch"):
        api_compat.clear_token()
        st.session_state.signed_out = True
        st.session_state.pop("user", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_overview() -> None:
    header(
        "SalesGenie / Overview",
        "Pipeline overview",
        "A single view of prospect volume, qualification health and the work waiting for you.",
        health_ok,
        health_payload,
    )

    if not health_ok:
        theme.empty_state(
            "Backend unavailable",
            "The interface is running, but no data can be loaded until the API responds.",
            "Start the API or update the connection URL in the sidebar.",
        )
        return

    ok, analytics = load_analytics()
    follow_ups = load_follow_ups()
    leads = st.session_state.leads_cache

    total = analytics.get("total_leads", len(leads)) if ok else len(leads)
    qualified = analytics.get("qualified_leads") if ok else None
    average = analytics.get("average_lead_score") if ok else None
    conversion = analytics.get("conversion_rate") if ok else None
    conversion_defined = analytics.get("conversion_rate_defined", False) if ok else False
    pipeline_value = analytics.get("pipeline_value") if ok else None
    pipeline_defined = analytics.get("pipeline_value_defined", False) if ok else False

    if not ok:
        theme.warning_note(
            "Live analytics could not be loaded. Only the lead directory is shown; "
            "qualification figures stay blank rather than guessing.",
            "Partial data",
        )

    cards = [
        theme.kpi("Total prospects", total, "All stored leads"),
        theme.kpi(
            "Qualified",
            qualified if qualified is not None else "n/a",
            "Stage qualified or later",
            "success" if qualified is not None else "muted",
        ),
        theme.kpi(
            "Average score",
            f"{average:.0f}" if isinstance(average, (int, float)) else "n/a",
            "Latest score per lead",
            "accent",
        ),
        theme.kpi(
            "Conversion rate",
            f"{conversion:.1f}%" if conversion_defined else "n/a",
            "Converted / total leads",
            "accent" if conversion_defined else "muted",
        ),
        theme.kpi(
            "Pipeline value",
            f"{pipeline_value:,.0f}" if pipeline_defined else "Not defined",
            "Awaiting an agreed definition" if not pipeline_defined else "Defined metric",
            "muted",
        ),
    ]
    st.markdown(theme.kpi_row(cards), unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1.35, 1], gap="large")

    with left:
        theme.section("Pipeline by stage", "Lead count in each lifecycle stage")
        distribution = analytics.get("pipeline_distribution") or []
        if distribution:
            frame = pd.DataFrame(distribution)
            frame["stage"] = frame["stage"].map(lambda value: STAGE_LABELS.get(value, str(value).title()))
            st.bar_chart(frame, x="stage", y="count", color="#E08D57", height=250)
        else:
            theme.empty_state("No pipeline data", "Stage distribution appears once leads exist.")

    with right:
        theme.section("Qualification bands", "Latest score per lead")
        hot = analytics.get("hot_leads", 0)
        warm = analytics.get("warm_leads", 0)
        cold = analytics.get("cold_leads", 0)
        if hot + warm + cold:
            frame = pd.DataFrame(
                {
                    "Band": ["Qualified (70+)", "Nurture (45-69)", "Low (<45)"],
                    "Leads": [hot, warm, cold],
                }
            )
            st.bar_chart(frame, x="Band", y="Leads", color="#F4B98F", height=250)
        else:
            theme.empty_state("No scores yet", "Score a lead in Lead Intelligence to populate this chart.")

    st.write("")
    left, right = st.columns([1.35, 1], gap="large")

    with left:
        theme.section("Recent prospects", "Newest records in the directory")
        if leads:
            frame = pd.DataFrame(
                [
                    {
                        "Company": lead.get("company_name"),
                        "Contact": lead.get("contact_name"),
                        "Industry": lead.get("industry"),
                        "Stage": STAGE_LABELS.get(lead.get("lead_status", ""), lead.get("lead_status")),
                    }
                    for lead in leads[:6]
                ]
            )
            st.dataframe(frame, width="stretch", hide_index=True)
            if st.button("Open leads workspace", icon=":material/arrow_forward:"):
                go("leads")
        else:
            theme.empty_state(
                "No prospects yet",
                "Add a lead manually or import a CSV to start building the pipeline.",
            )
            if st.button("Add the first lead", type="primary", icon=":material/add:"):
                go("leads")

    with right:
        theme.section("Follow-ups", "Open recommendations from stored scores")
        if follow_ups:
            for item in follow_ups[:4]:
                st.markdown(
                    '<div class="sg-card" style="margin-bottom:0.6rem;">'
                    f'<div style="display:flex;justify-content:space-between;gap:0.6rem;">'
                    f'<span style="font-weight:650;font-size:0.9rem;">{esc(item.get("company_name"))}</span>'
                    f'{status_badge(item.get("priority", ""))}</div>'
                    f'<div class="sg-muted" style="margin-top:0.3rem;">{esc(item.get("action"))}</div>'
                    "</div>",
                    unsafe_allow_html=True,
                )
        else:
            theme.empty_state(
                "Nothing pending",
                "Follow-ups appear here when a stored score recommends an action.",
            )

    trend = analytics.get("activity_trend") or []
    if ok and trend:
        st.write("")
        theme.section("Recent activity", "Leads created per day over the last 14 days")
        st.line_chart(
            pd.DataFrame(trend),
            x="date",
            y="activity",
            color="#E08D57",
            height=200,
        )


def page_leads() -> None:
    header(
        "SalesGenie / Leads",
        "Leads",
        "Capture prospects, import datasets and keep the directory clean.",
        health_ok,
        health_payload,
    )

    leads = st.session_state.leads_cache
    directory, add_tab, import_tab = st.tabs(["Directory", "Add lead", "Import CSV"])

    with directory:
        if not leads:
            theme.empty_state(
                "The directory is empty",
                "Create a lead with the form or import a CSV, then return here to filter and open it.",
            )
        else:
            filter_col, industry_col, stage_col = st.columns([2.2, 1, 1], gap="medium")
            with filter_col:
                query = st.text_input(
                    "Search", placeholder="Search company or contact", label_visibility="collapsed"
                )
            with industry_col:
                industries = sorted({lead.get("industry") for lead in leads if lead.get("industry")})
                industry = st.selectbox(
                    "Industry", ["All industries"] + industries, label_visibility="collapsed"
                )
            with stage_col:
                stages = sorted({lead.get("lead_status") for lead in leads if lead.get("lead_status")})
                stage = st.selectbox(
                    "Stage", ["All stages"] + stages, label_visibility="collapsed"
                )

            filtered = leads
            if query:
                needle = query.lower()
                filtered = [
                    lead
                    for lead in filtered
                    if needle in str(lead.get("company_name", "")).lower()
                    or needle in str(lead.get("contact_name", "")).lower()
                    or needle in str(lead.get("email", "")).lower()
                ]
            if industry != "All industries":
                filtered = [lead for lead in filtered if lead.get("industry") == industry]
            if stage != "All stages":
                filtered = [lead for lead in filtered if lead.get("lead_status") == stage]

            st.caption(f"{len(filtered)} of {len(leads)} prospects")

            if not filtered:
                theme.empty_state("No matching prospects", "Adjust the filters to widen the search.")
            else:
                frame = pd.DataFrame(
                    [
                        {
                            "Company": lead.get("company_name"),
                            "Contact": lead.get("contact_name"),
                            "Industry": lead.get("industry"),
                            "Email": lead.get("email"),
                            "Stage": STAGE_LABELS.get(lead.get("lead_status", ""), lead.get("lead_status")),
                        }
                        for lead in filtered
                    ]
                )
                event = st.dataframe(
                    frame,
                    width="stretch",
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="lead_directory",
                )
                rows = getattr(getattr(event, "selection", None), "rows", []) or []
                if rows:
                    selected = filtered[rows[0]]
                    st.session_state.selected_lead_id = selected["lead_id"]
                    score = load_score(selected["lead_id"])
                    score_value = score.get("lead_score") if score else None
                    label, tone = band_for(score_value)
                    st.markdown(
                        '<div class="sg-card" style="margin-top:0.8rem;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">'
                        f'<div><div style="font-weight:700;font-size:1.05rem;">{esc(selected.get("company_name"))}</div>'
                        f'<div class="sg-muted">{esc(selected.get("contact_name") or "No contact")} · '
                        f'{esc(selected.get("email") or "No email")}</div></div>'
                        f'<div>{theme.badge(label, tone)}</div></div>'
                        '<div style="height:0.8rem;"></div>'
                        + theme.meta_row(
                            [
                                ("Industry", selected.get("industry") or "-"),
                                ("Company size", selected.get("company_size") or "-"),
                                ("Funding", selected.get("funding_stage") or "-"),
                                ("Stage", STAGE_LABELS.get(selected.get("lead_status", ""), selected.get("lead_status") or "-")),
                            ]
                        )
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    action_one, action_two, action_three = st.columns(3, gap="medium")
                    if action_one.button("Open intelligence", icon=":material/psychology:", width="stretch"):
                        go("intelligence", selected["lead_id"])
                    if action_two.button("Write outreach", icon=":material/edit_note:", width="stretch"):
                        go("outreach", selected["lead_id"])
                    if action_three.button("Summarise a call", icon=":material/forum:", width="stretch"):
                        go("conversations", selected["lead_id"])

    with add_tab:
        with st.form("add_lead"):
            left, right = st.columns(2, gap="large")
            with left:
                theme.section("Company and contact")
                company = st.text_input("Company name *", placeholder="Apex Global Solutions")
                contact = st.text_input("Contact name *", placeholder="Sarah Jenkins")
                email = st.text_input("Business email *", placeholder="sarah@apex.com")
                phone = st.text_input("Phone", placeholder="+1 415 555 0192")
            with right:
                theme.section("Firmographics")
                industry = st.selectbox(
                    "Industry",
                    [
                        "Enterprise Software",
                        "Artificial Intelligence",
                        "Cloud Computing",
                        "Fintech",
                        "Healthcare AI",
                        "Cybersecurity",
                        "E-Commerce",
                        "Other",
                    ],
                )
                size = st.selectbox(
                    "Company size",
                    [
                        "1-50 employees",
                        "50-100 employees",
                        "100-250 employees",
                        "250-500 employees",
                        "500+ employees",
                    ],
                    index=3,
                )
                funding = st.selectbox(
                    "Funding stage",
                    ["Seed", "Series A", "Series B", "Series C", "Series D", "Growth", "Bootstrapped", "Public / IPO"],
                    index=3,
                )
                status = st.selectbox("Pipeline stage", ["New", "Contacted", "Qualified", "Proposal Sent"])
            need = st.text_area(
                "Core need",
                placeholder="What is the prospect trying to change, and why now?",
                height=100,
            )
            submitted = st.form_submit_button(
                "Save prospect", type="primary", width="stretch"
            )

        if submitted:
            errors = []
            if len(company.strip()) < 2:
                errors.append("Company name is required.")
            if len(contact.strip()) < 2:
                errors.append("Contact name is required.")
            if "@" not in email or "." not in email:
                errors.append("A valid business email is required.")
            if errors:
                for message in errors:
                    theme.error_note(message)
            else:
                payload = {
                    "company_name": company.strip(),
                    "industry": industry,
                    "contact_name": contact.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "company_size": size,
                    "funding_stage": funding,
                    "business_need": need.strip(),
                    "lead_status": status,
                }
                with st.spinner("Saving prospect..."):
                    ok, response = api_post("/leads/", json_data=payload)
                if ok:
                    new_id = (response.get("lead") or {}).get("lead_id")
                    st.session_state.selected_lead_id = new_id
                    load_leads(force=True)
                    st.toast("Prospect saved.")
                    st.rerun()
                else:
                    theme.error_note(response.get("error", "The prospect could not be saved."))

    with import_tab:
        left, right = st.columns([2, 1], gap="large")
        with left:
            uploaded = st.file_uploader(
                "Prospect dataset (.csv)",
                type=["csv"],
                help="Required column: company_name. Optional: industry, contact_name, email, phone, company_size, funding_stage, business_need.",
            )
        with right:
            template = (
                "company_name,industry,contact_name,email,phone,company_size,funding_stage,business_need\n"
                "TechCorp Solutions,Enterprise Software,Sarah Johnson,sarah@techcorp.com,+1234567890,250-500 employees,Series C,Scaling data operations\n"
                "InnovateAI Labs,Artificial Intelligence,Mark Chen,mark@innovateai.com,+9876543210,50-100 employees,Series A,Building AI pipelines\n"
            )
            st.download_button(
                "Download template",
                data=template,
                file_name="salesgenie_prospect_template.csv",
                mime="text/csv",
                icon=":material/download:",
                width="stretch",
            )

        if uploaded is not None:
            try:
                frame = pd.read_csv(uploaded)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                theme.error_note(f"The file could not be parsed: {exc}")
            else:
                st.caption(f"{len(frame)} rows parsed")
                st.dataframe(frame.head(6), width="stretch", hide_index=True)
                if "company_name" not in frame.columns:
                    theme.error_note("The file must contain a company_name column.")
                elif st.button(
                    "Import valid rows", type="primary", icon=":material/upload_file:"
                ):
                    records = []
                    for _, row in frame.iterrows():
                        record = {
                            "company_name": str(row.get("company_name", "")).strip(),
                            "industry": str(row.get("industry", "Other")).strip()
                            if pd.notna(row.get("industry"))
                            else "Other",
                            "contact_name": str(row.get("contact_name", "")).strip()
                            if pd.notna(row.get("contact_name"))
                            else "",
                            "email": str(row.get("email", "")).strip()
                            if pd.notna(row.get("email"))
                            else "",
                            "phone": str(row.get("phone", "")).strip()
                            if pd.notna(row.get("phone"))
                            else "",
                            "company_size": str(row.get("company_size", "100-250 employees")).strip()
                            if pd.notna(row.get("company_size"))
                            else "100-250 employees",
                            "funding_stage": str(row.get("funding_stage", "Growth")).strip()
                            if pd.notna(row.get("funding_stage"))
                            else "Growth",
                            "business_need": str(row.get("business_need", "")).strip()
                            if pd.notna(row.get("business_need"))
                            else "",
                            "lead_status": "New",
                        }
                        if record["company_name"]:
                            records.append(record)

                    if not records:
                        theme.error_note("No row has a company name, so nothing was imported.")
                    else:
                        with st.spinner(f"Importing {len(records)} rows..."):
                            ok, response = api_post("/leads/bulk", json_data=records, timeout=60)
                        if ok:
                            theme.success_note(response.get("message", "Import completed."))
                            report = response.get("report") or {}
                            if report.get("errors"):
                                st.dataframe(
                                    pd.DataFrame(report["errors"]),
                                    width="stretch",
                                    hide_index=True,
                                )
                            load_leads(force=True)
                            st.toast("Import completed.")
                        else:
                            theme.error_note(response.get("error", "The import failed."))


def page_intelligence() -> None:
    header(
        "SalesGenie / Lead Intelligence",
        "Lead intelligence",
        "Company research, qualification and an explainable score for the selected prospect.",
        health_ok,
        health_payload,
    )

    leads = st.session_state.leads_cache
    if not leads:
        theme.empty_state(
            "No prospects to analyse",
            "Add or import a lead first; intelligence runs against a stored prospect record.",
        )
        return

    lead = pick_lead(leads, key="intel_lead", label="Prospect to analyse")
    if not lead:
        return
    lead_id = lead["lead_id"]

    left, right = st.columns([1, 1], gap="medium")
    analyse = left.button(
        "Analyse company", type="primary", icon=":material/search:", width="stretch"
    )
    score_btn = right.button(
        "Compute score", icon=":material/calculate:", width="stretch"
    )

    if analyse:
        with st.spinner("Analysing the company..."):
            ok, response = api_post(f"/intelligence/analyze/{lead_id}", timeout=60)
        if ok:
            st.session_state.insights_cache[lead_id] = response
            st.toast("Analysis ready.")
            st.rerun()
        else:
            theme.error_note(response.get("error", "Analysis failed."))

    if score_btn:
        with st.spinner("Computing the qualification score..."):
            ok, response = api_post(f"/intelligence/score/{lead_id}", timeout=60)
        if ok:
            st.session_state.scores_cache[lead_id] = response
            st.toast("Score computed.")
            st.rerun()
        else:
            theme.error_note(response.get("error", "Scoring failed."))

    score = load_score(lead_id)
    insight = load_insight(lead_id)

    st.write("")
    theme.section("Qualification", "Deterministic score with its factor breakdown")
    if not score:
        theme.empty_state(
            "No score yet",
            "Compute a score to see the qualification band, the factors and the next best action.",
        )
    else:
        value = score.get("lead_score", 0)
        label, tone = band_for(value)
        color = theme.TONE[tone] if tone in theme.TONE else theme.PALETTE["text"]
        probability = score.get("conversion_probability")
        if probability is None:
            probability_display = "n/a"
            probability_note = "No calibrated model configured"
        else:
            numeric = float(probability)
            probability_display = f"{numeric * 100:.1f}%" if numeric <= 1 else f"{numeric:.1f}%"
            probability_note = "Reported by the backend"

        st.markdown(
            '<div class="sg-card" style="display:flex;gap:2.2rem;flex-wrap:wrap;align-items:flex-start;">'
            f'<div><div class="sg-kpi-label">Score</div>'
            f'<div style="font-size:2.9rem;font-weight:700;line-height:1;color:{color};">'
            f'{esc(value)}<span style="font-size:1rem;color:#777487;">/100</span></div>'
            f'<div style="margin-top:0.4rem;">{theme.badge(label, tone)}</div></div>'
            f'<div><div class="sg-kpi-label">Conversion probability</div>'
            f'<div style="font-size:1.5rem;font-weight:700;margin-top:0.2rem;">{esc(probability_display)}</div>'
            f'<div class="sg-muted">{esc(probability_note)}</div></div>'
            f'<div style="flex:1;min-width:220px;"><div class="sg-kpi-label">Recommended next action</div>'
            f'<div style="font-size:0.92rem;font-weight:550;margin-top:0.25rem;line-height:1.55;">'
            f'{para(score.get("next_action") or "-")}</div>'
            f'<div class="sg-muted" style="margin-top:0.4rem;">Model: '
            f'{esc(score.get("model_version") or "heuristic")}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        if score.get("reason"):
            st.caption(score["reason"])

        factors = score.get("factors_detail") or []
        if factors:
            theme.section("Score factors", "Weight, contribution and evidence for each factor")
            frame = pd.DataFrame(
                [
                    {
                        "Factor": factor.get("name"),
                        "Dimension": factor.get("dimension") or "-",
                        "Weight": factor.get("weight"),
                        "Value": factor.get("value"),
                        "Points": factor.get("points"),
                        "Signal": factor.get("signal") or "-",
                    }
                    for factor in factors
                ]
            )
            st.dataframe(frame, width="stretch", hide_index=True)
            with st.expander("Why each factor scored this way"):
                for factor in factors:
                    st.markdown(
                        f"**{esc(factor.get('name'))}** - {esc(factor.get('explanation') or 'No explanation supplied.')}"
                    )

        positive = score.get("positive_signals") or []
        negative = score.get("negative_signals") or []
        missing = score.get("missing_information") or []
        if positive or negative or missing:
            with st.expander("Signals and gaps"):
                columns = st.columns(3, gap="medium")
                columns[0].markdown("**Positive**" + bullet_list(positive), unsafe_allow_html=True)
                columns[1].markdown("**Negative**" + bullet_list(negative), unsafe_allow_html=True)
                columns[2].markdown("**Missing**" + bullet_list(missing), unsafe_allow_html=True)

    st.write("")
    theme.section("Company intelligence", "Supplied facts are separated from generated hypotheses")
    if not insight:
        theme.empty_state(
            "No analysis yet",
            "Run an analysis to see the company overview, needs, opportunities and open questions.",
        )
        return

    st.markdown(
        theme.card("Company overview", para(insight.get("industry_situation")), "neutral"),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            '<div class="sg-card"><div style="display:flex;justify-content:space-between;align-items:center;">'
            '<div class="sg-kpi-label">Supplied facts</div>'
            + theme.badge("Backend record", "success")
            + "</div>"
            + bullet_list(insight.get("supported_facts"))
            + "</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="sg-card"><div style="display:flex;justify-content:space-between;align-items:center;">'
            '<div class="sg-kpi-label">Generated hypotheses</div>'
            + theme.badge("Validate in discovery", "warning")
            + "</div>"
            + bullet_list(
                (insight.get("needs_detail") or [])
                + (insight.get("opportunities_detail") or [])
                + (insight.get("potential_challenges") or [])
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            theme.card("Product and industry fit", para(insight.get("product_industry_fit") or "-")),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            theme.card("Buyer relevance", para(insight.get("buyer_role_relevance") or "-")),
            unsafe_allow_html=True,
        )

    questions = insight.get("discovery_questions") or []
    missing = insight.get("missing_information") or []
    if questions or missing:
        with st.expander("Discovery questions and missing information"):
            st.markdown("**Questions to ask**" + bullet_list(questions), unsafe_allow_html=True)
            st.markdown("**Still missing**" + bullet_list(missing), unsafe_allow_html=True)

    st.caption(
        f"Qualification: {insight.get('qualification_category') or 'not assessed'} · "
        f"Confidence: {insight.get('confidence') or 'low'}"
    )


def page_outreach() -> None:
    header(
        "SalesGenie / Outreach Studio",
        "Outreach studio",
        "Generate, edit and review a personalised message. Generation and delivery are separate.",
        health_ok,
        health_payload,
    )

    leads = st.session_state.leads_cache
    if not leads:
        theme.empty_state(
            "No prospects to write to",
            "Add a lead first; outreach is generated from a stored prospect record.",
        )
        return

    lead = pick_lead(leads, key="outreach_lead", label="Prospect")
    if not lead:
        return
    lead_id = lead["lead_id"]

    # A draft belongs to one prospect.  Switching prospects clears the editor
    # instead of leaving the previous message in place.
    if st.session_state.draft_lead_id != lead_id:
        st.session_state.draft_lead_id = lead_id
        st.session_state.email_subject = ""
        st.session_state.email_body = ""
        st.session_state.pop("studio_subject", None)
        st.session_state.pop("studio_body", None)

    # Read the newest stored draft once per prospect rather than on every rerun.
    if lead_id not in st.session_state.draft_checked:
        st.session_state.draft_checked[lead_id] = True
        saved_ok, saved = api_get(f"/intelligence/outreach/{lead_id}", timeout=10)
        if saved_ok:
            st.session_state.email_subject = saved.get("email_subject", "")
            st.session_state.email_body = saved.get("email_content", "")

    st.markdown(
        '<div class="sg-card-cream">'
        + theme.meta_row(
            [
                ("Company", lead.get("company_name") or "-"),
                ("Contact", lead.get("contact_name") or "-"),
                ("Email", lead.get("email") or "No email on record"),
                ("Industry", lead.get("industry") or "-"),
            ]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    left, right = st.columns([1, 2], gap="large")

    with left:
        theme.section("Recommendation", "From the stored score and lead signals")
        if st.button("Load recommendation", icon=":material/lightbulb:", width="stretch"):
            ok, data = api_get(f"/recommendations/{lead_id}", timeout=20)
            st.session_state.recommendation_cache[lead_id] = data if ok else None
            if not ok:
                theme.error_note(data.get("error", "No recommendation available."))

        recommendation = st.session_state.recommendation_cache.get(lead_id)
        if recommendation:
            priority = str(recommendation.get("priority") or "").lower()
            tone = {"high": "success", "medium": "warning", "low": "muted"}.get(priority, "muted")
            st.markdown(
                '<div class="sg-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span class="sg-kpi-label">Priority</span>{theme.badge(priority.capitalize() or "Unknown", tone)}</div>'
                f'<div style="margin-top:0.6rem;font-weight:600;font-size:0.9rem;">{para(recommendation.get("recommended_action") or "-")}</div>'
                f'<div class="sg-muted" style="margin-top:0.4rem;">Timing: {esc(recommendation.get("suggested_timing") or "Not set")}</div>'
                f'<div class="sg-muted">Channel: {esc(recommendation.get("suggested_channel") or "Not set")}</div>'
                f'<div class="sg-muted" style="margin-top:0.4rem;">{para(recommendation.get("reason") or "")}</div>'
                "</div>",
                unsafe_allow_html=True,
            )
            if recommendation.get("follow_up_draft"):
                with st.expander("Suggested follow-up draft"):
                    st.write(recommendation["follow_up_draft"])
        else:
            st.caption("Load the recommendation to see priority, timing and channel.")

    with right:
        theme.section("Draft", "Tone, length and channel are sent to the backend")
        with st.form("outreach_form"):
            row_one, row_two, row_three = st.columns(3, gap="medium")
            tone_label = row_one.selectbox("Tone", ["Professional", "Friendly", "Direct", "Formal"])
            length = row_two.selectbox("Length", ["short", "medium", "long"], index=1)
            channel = row_three.selectbox(
                "Channel",
                ["cold_email", "follow_up", "linkedin_message", "call_script", "short_message"],
                format_func=lambda value: value.replace("_", " ").title(),
            )
            goal = st.text_input("Goal", value="start a discovery conversation")
            cta = st.text_input("Call to action", value="Would a short conversation next week be useful?")
            pain_points = st.text_area(
                "Known pain points (one per line)", height=80, placeholder="Manual reporting\nSlow onboarding"
            )
            generate = st.form_submit_button(
                "Generate draft", type="primary", icon=":material/auto_awesome:", width="stretch"
            )

        if generate:
            payload = {
                "lead_id": lead_id,
                "tone": tone_label.lower(),
                "length": length,
                "outreach_type": channel,
                "goal": goal.strip(),
                "call_to_action": cta.strip(),
                "pain_points": [line.strip() for line in pain_points.splitlines() if line.strip()],
                "industry": lead.get("industry") or "",
            }
            with st.spinner("Generating the draft..."):
                ok, response = api_post("/intelligence/outreach", json_data=payload, timeout=60)
            if ok:
                st.session_state.email_subject = response.get("email_subject", "")
                st.session_state.email_body = response.get("email_content", "")
                st.session_state.email_tone = tone_label.lower()
                st.session_state["studio_subject"] = st.session_state.email_subject
                st.session_state["studio_body"] = st.session_state.email_body
                st.toast("Draft generated.")
                st.rerun()
            else:
                theme.error_note(response.get("error", "Draft generation failed."))

        st.session_state.setdefault("studio_subject", st.session_state.email_subject)
        st.session_state.setdefault("studio_body", st.session_state.email_body)

        subject = st.text_input("Subject", key="studio_subject")
        body = st.text_area(
            "Message",
            key="studio_body",
            height=260,
            placeholder="Generate a draft, or write the message here.",
        )
        st.session_state.email_subject = subject
        st.session_state.email_body = body

        words = len(body.split()) if body else 0
        st.caption(f"{words} words · {len(body)} characters · tone {tone_label.lower()}")

        action_one, action_two = st.columns(2, gap="medium")
        with action_one:
            with st.expander("Copy message"):
                st.code(f"Subject: {subject}\n\n{body}" if (subject or body) else "Nothing to copy yet.")
        with action_two:
            send = st.button(
                "Send email", icon=":material/send:", width="stretch", disabled=not (subject and body)
            )
            st.caption("Delivery requires a configured provider in the backend.")
        if send:
            if not lead.get("email"):
                theme.error_note("This prospect has no email address on record.")
            else:
                with st.spinner("Checking delivery configuration..."):
                    ok, response = api_post(
                        "/outreach/send-email",
                        json_data={
                            "lead_id": lead_id,
                            "recipient_email": lead.get("email"),
                            "subject": subject,
                            "body": body,
                        },
                        timeout=20,
                    )
                message = response.get("message") or "E-mail delivery is not configured."
                theme.warning_note(f"Not sent. {message}", "Delivery is not configured")


def page_conversations() -> None:
    header(
        "SalesGenie / Conversations",
        "Conversations",
        "Turn a call transcript into a summary, action items and a clear next step.",
        health_ok,
        health_payload,
    )

    leads = st.session_state.leads_cache
    if not leads:
        theme.empty_state(
            "No prospects yet",
            "Add a lead before summarising a conversation.",
        )
        return

    lead = pick_lead(leads, key="conversation_lead", label="Prospect")
    if not lead:
        return
    lead_id = lead["lead_id"]

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        theme.section("New summary", "The backend extracts only what the transcript contains")
        with st.form("conversation_form"):
            interaction_type = st.selectbox(
                "Interaction type",
                ["call", "meeting", "demo", "email", "note"],
                format_func=lambda value: value.capitalize(),
            )
            transcript = st.text_area(
                "Transcript", height=220, placeholder="Paste the call transcript here..."
            )
            notes = st.text_area(
                "Notes", height=90, placeholder="Optional notes or context..."
            )
            submitted = st.form_submit_button(
                "Summarise", type="primary", icon=":material/summarize:", width="stretch"
            )

        if submitted:
            if not transcript.strip() and not notes.strip():
                theme.error_note("Provide a transcript or notes to summarise.")
            else:
                with st.spinner("Summarising the conversation..."):
                    ok, response = api_post(
                        "/conversations/summarize",
                        json_data={
                            "lead_id": lead_id,
                            "transcript": transcript,
                            "notes": notes,
                            "interaction_type": interaction_type,
                        },
                        timeout=60,
                    )
                if ok:
                    st.session_state.conversations_cache[lead_id] = response
                    st.session_state.pop(f"_conversation_history_at_{lead_id}", None)
                    st.session_state.pop(f"_conversation_history_{lead_id}", None)
                    st.toast("Summary saved.")
                    st.rerun()
                else:
                    theme.error_note(response.get("error", "The conversation could not be summarised."))

    with right:
        theme.section("Latest summary", "Stored against the prospect")
        summary = st.session_state.conversations_cache.get(lead_id)
        if not summary:
            theme.empty_state(
                "No summary yet",
                "Paste a transcript and summarise it to see key points and action items.",
            )
        else:
            st.markdown(
                theme.card("Summary", para(summary.get("summary") or "-")),
                unsafe_allow_html=True,
            )
            action_items = summary.get("action_items") or []
            if action_items:
                rows = []
                for item in action_items:
                    if isinstance(item, dict):
                        rows.append(
                            {
                                "Action": item.get("action", ""),
                                "Owner": item.get("owner") or "Unassigned",
                                "Due": item.get("due_date") or "No date",
                            }
                        )
                    else:
                        rows.append({"Action": str(item), "Owner": "Unassigned", "Due": "No date"})
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            if summary.get("suggested_follow_up"):
                st.markdown(
                    theme.card(
                        "Suggested follow-up",
                        para(summary["suggested_follow_up"]),
                        "accent",
                    ),
                    unsafe_allow_html=True,
                )

    st.write("")
    theme.section("History", "Previous summaries for this prospect")
    history_key = f"_conversation_history_{lead_id}"
    history_stamp = f"_conversation_history_at_{lead_id}"
    if history_key not in st.session_state or not _fresh(history_stamp, 20):
        ok, rows = api_get(f"/leads/{lead_id}/conversations", timeout=10)
        st.session_state[history_key] = rows if ok and isinstance(rows, list) else []
        st.session_state[history_stamp] = time.time()

    history = st.session_state.get(history_key) or []
    if not history:
        theme.empty_state("No stored conversations", "Summaries are saved against the prospect automatically.")
    else:
        for index, item in enumerate(history[:10]):
            with st.expander(
                f"{when(item.get('created_at'))} · {str(item.get('interaction_type') or 'interaction').capitalize()}"
            ):
                st.write(item.get("summary") or "No summary text.")
                if item.get("key_points"):
                    st.markdown("**Key points**" + bullet_list(item["key_points"]), unsafe_allow_html=True)

    follow_ups = [item for item in load_follow_ups() if str(item.get("lead_id")) == str(lead_id)]
    if follow_ups:
        st.write("")
        theme.section("Follow-ups for this prospect")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Priority": item.get("priority", "").capitalize(),
                        "Action": item.get("action"),
                        "Score": item.get("score"),
                        "Reason": item.get("reason"),
                    }
                    for item in follow_ups
                ]
            ),
            width="stretch",
            hide_index=True,
        )


def page_analytics() -> None:
    header(
        "SalesGenie / Analytics",
        "Analytics",
        "Pipeline distribution, qualification health and the follow-ups that need attention.",
        health_ok,
        health_payload,
    )

    ok, analytics = load_analytics()
    if not ok:
        theme.empty_state(
            "Analytics unavailable",
            "The backend did not return analytics. Check the connection and try again.",
        )
        return

    total = analytics.get("total_leads", 0)
    qualified = analytics.get("qualified_leads", 0)
    converted = analytics.get("converted_leads", 0)
    average = analytics.get("average_lead_score")
    conversion_defined = analytics.get("conversion_rate_defined", False)

    cards = [
        theme.kpi("Total prospects", total, "All stored leads"),
        theme.kpi("Qualified", qualified, f"{converted} converted", "success"),
        theme.kpi(
            "Average score",
            f"{average:.0f}" if isinstance(average, (int, float)) else "n/a",
            "Latest score per lead",
            "accent",
        ),
        theme.kpi(
            "Conversion rate",
            f"{analytics.get('conversion_rate', 0):.1f}%" if conversion_defined else "n/a",
            "Converted / total leads" if conversion_defined else "Not enough data",
            "accent" if conversion_defined else "muted",
        ),
    ]
    st.markdown(theme.kpi_row(cards), unsafe_allow_html=True)

    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        theme.section("Pipeline by stage")
        distribution = analytics.get("pipeline_distribution") or []
        if distribution:
            frame = pd.DataFrame(distribution)
            frame["stage"] = frame["stage"].map(lambda value: STAGE_LABELS.get(value, str(value).title()))
            st.bar_chart(frame, x="stage", y="count", color="#E08D57", height=260)
        else:
            theme.empty_state("No pipeline data", "Stage distribution appears once leads exist.")

    with right:
        theme.section("Qualification bands")
        frame = pd.DataFrame(
            {
                "Band": ["Qualified (70+)", "Nurture (45-69)", "Low (<45)"],
                "Leads": [
                    analytics.get("hot_leads", 0),
                    analytics.get("warm_leads", 0),
                    analytics.get("cold_leads", 0),
                ],
            }
        )
        if frame["Leads"].sum():
            st.bar_chart(frame, x="Band", y="Leads", color="#F4B98F", height=260)
        else:
            theme.empty_state("No scores yet", "Score a lead to populate this chart.")

    trend = analytics.get("activity_trend") or []
    if trend:
        st.write("")
        theme.section("Activity, last 14 days", "Leads created per day")
        trend_frame = pd.DataFrame(trend)
        st.line_chart(trend_frame, x="date", y="activity", color="#E08D57", height=220)

    st.write("")
    theme.section("Follow-ups", "Derived from stored scores; read-only by design")
    follow_ups = load_follow_ups()
    if follow_ups:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Company": item.get("company_name"),
                        "Priority": item.get("priority", "").capitalize(),
                        "Score": item.get("score"),
                        "Recommended action": item.get("action"),
                        "Reason": item.get("reason"),
                    }
                    for item in follow_ups
                ]
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        theme.empty_state("Nothing pending", "Follow-ups appear when a stored score recommends an action.")

    st.write("")
    theme.section("Narrative insights", "Observations over the supplied aggregates only")
    if st.button("Generate insights", icon=":material/insights:"):
        with st.spinner("Reading the aggregates..."):
            ok, response = api_post("/analytics/insights", json_data={}, timeout=40)
        if ok:
            st.session_state["_analytics_insights"] = response
        else:
            theme.error_note(response.get("error", "Insights could not be generated."))

    insights = st.session_state.get("_analytics_insights")
    if insights:
        for item in insights.get("insights") or []:
            st.markdown(
                theme.card(
                    item.get("title") or "Observation",
                    para(item.get("observation") or ""),
                    "neutral",
                    footer=f"Evidence: {esc(item.get('evidence') or '-')}",
                ),
                unsafe_allow_html=True,
            )
        if insights.get("caveat"):
            st.caption(insights["caveat"])


PAGES = {
    "overview": page_overview,
    "leads": page_leads,
    "intelligence": page_intelligence,
    "outreach": page_outreach,
    "conversations": page_conversations,
    "analytics": page_analytics,
}

PAGES.get(st.session_state.nav, page_overview)()

st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;'
    'color:#777487;font-size:0.76rem;padding-bottom:1rem;">'
    "<span>SalesGenie AI · Sales intelligence platform</span>"
    "<span>Streamlit · FastAPI · PostgreSQL</span></div>",
    unsafe_allow_html=True,
)
