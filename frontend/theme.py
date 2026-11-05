"""Design system for the SalesGenie frontend.

Warm peach-and-cream palette, Inter typography and a small set of reusable
HTML components.  Everything here is presentation only: no API calls, no
session state and no data of its own.

The palette follows the agreed direction, with two contrast adjustments:

* ``ACCENT_STRONG`` (#E08D57) is used where white text must sit on the accent
  (Streamlit's primary buttons), because the soft accent (#F4B98F) does not
  carry white text at 4.5:1.
* ``MUTED`` (#777487) is used only for secondary labels at 14px or larger.
"""
from __future__ import annotations

import html

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#FFF5EF",
    "bg_alt": "#FBE5D7",
    "surface": "#FFFFFF",
    "cream": "#FFF0E2",
    "accent": "#F4B98F",
    "accent_hover": "#EBA77A",
    "accent_strong": "#E08D57",
    "text": "#29263A",
    "muted": "#777487",
    "border": "#F0E3DA",
    "success": "#398568",
    "warning": "#B77935",
    "error": "#C45454",
}

RADIUS = {"sm": "10px", "md": "14px", "lg": "18px", "xl": "22px"}

TONE = {
    "neutral": PALETTE["text"],
    "muted": PALETTE["muted"],
    "accent": "#B4652F",
    "success": PALETTE["success"],
    "warning": PALETTE["warning"],
    "error": PALETTE["error"],
}

TONE_BG = {
    "neutral": "#F6F1EC",
    "muted": "#F6F1EC",
    "accent": "#FDEBDD",
    "success": "#E8F3EE",
    "warning": "#FBF0E0",
    "error": "#FAEAEA",
}


def esc(value) -> str:
    """HTML-escape any value that will be interpolated into markup."""
    return html.escape(str(value if value is not None else ""))


def css() -> str:
    p = PALETTE
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {{
  --sg-bg: {p['bg']};
  --sg-bg-alt: {p['bg_alt']};
  --sg-surface: {p['surface']};
  --sg-cream: {p['cream']};
  --sg-accent: {p['accent']};
  --sg-accent-hover: {p['accent_hover']};
  --sg-accent-strong: {p['accent_strong']};
  --sg-text: {p['text']};
  --sg-muted: {p['muted']};
  --sg-border: {p['border']};
  --sg-success: {p['success']};
  --sg-warning: {p['warning']};
  --sg-error: {p['error']};
}}

html, body, [class*="css"] {{
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}}

[data-testid="stAppViewContainer"] {{
  background: var(--sg-bg);
  color: var(--sg-text);
}}
[data-testid="stHeader"] {{
  background: transparent;
  height: 0;
}}
[data-testid="stToolbar"] {{ display: none; }}
.stAppDeployButton, [data-testid="stAppDeployButton"] {{ display: none; }}
#MainMenu, footer {{ visibility: hidden; }}

.block-container {{
  padding: 1.4rem 2.4rem 3rem 2.4rem;
  max-width: 1380px;
}}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{
  background: var(--sg-bg-alt);
  border-right: 1px solid var(--sg-border);
}}
[data-testid="stSidebar"] > div:first-child {{
  padding-top: 1.2rem;
}}
[data-testid="stSidebar"] hr {{
  border-color: var(--sg-border);
  margin: 0.9rem 0;
}}

/* ---------- Typography ---------- */
h1, h2, h3, h4, h5 {{
  color: var(--sg-text);
  letter-spacing: -0.015em;
}}
p, li, label, span {{ color: var(--sg-text); }}

.sg-eyebrow {{
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--sg-muted);
  margin-bottom: 0.25rem;
}}
.sg-page-title {{
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.2;
  margin: 0 0 0.35rem 0;
  color: var(--sg-text);
}}
.sg-page-sub {{
  font-size: 0.92rem;
  color: var(--sg-muted);
  margin: 0;
  max-width: 62ch;
}}
.sg-section-title {{
  font-size: 1.02rem;
  font-weight: 650;
  margin: 0;
  color: var(--sg-text);
}}
.sg-section-sub {{
  font-size: 0.82rem;
  color: var(--sg-muted);
  margin: 0.15rem 0 0 0;
}}

/* ---------- Cards ---------- */
.sg-card {{
  background: var(--sg-surface);
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['lg']};
  padding: 1.15rem 1.25rem;
  box-shadow: 0 1px 2px rgba(41, 38, 58, 0.04);
}}
.sg-card-cream {{
  background: var(--sg-cream);
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['lg']};
  padding: 1.15rem 1.25rem;
}}
.sg-kpi {{
  background: var(--sg-surface);
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['md']};
  padding: 1rem 1.1rem;
  min-height: 118px;
  flex: 1;
  width: 100%;
  box-sizing: border-box;
  box-shadow: 0 1px 2px rgba(41, 38, 58, 0.04);
}}
.sg-kpi-label {{
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--sg-muted);
}}
.sg-kpi-value {{
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0.4rem 0 0.15rem 0;
}}
.sg-kpi-meta {{
  font-size: 0.78rem;
  color: var(--sg-muted);
}}

/* ---------- Badges ---------- */
.sg-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.5;
}}
.sg-dot {{
  width: 7px; height: 7px; border-radius: 50%;
  display: inline-block;
}}

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius: {RADIUS['sm']};
  border: 1px solid var(--sg-border);
  background: var(--sg-surface);
  color: var(--sg-text);
  font-weight: 600;
  font-size: 0.88rem;
  padding: 0.5rem 1rem;
  transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
  box-shadow: none;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
  background: var(--sg-cream);
  border-color: var(--sg-accent);
  color: var(--sg-text);
}}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {{
  outline: 2px solid var(--sg-accent-strong);
  outline-offset: 2px;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: var(--sg-accent-strong);
  border-color: var(--sg-accent-strong);
  color: #FFFFFF;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
  background: #CE7A45;
  border-color: #CE7A45;
  color: #FFFFFF;
}}
.stButton > button:disabled {{
  background: #F7F0EA;
  color: #A9A3B3;
  border-color: var(--sg-border);
}}

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
  background: var(--sg-surface) !important;
  border-color: var(--sg-border) !important;
  border-radius: {RADIUS['sm']} !important;
}}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {{
  border-color: var(--sg-accent-strong) !important;
  box-shadow: 0 0 0 2px rgba(224, 141, 87, 0.18) !important;
}}
[data-testid="stWidgetLabel"] p {{
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--sg-text);
}}

/* ---------- Tabs ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  gap: 4px;
  background: var(--sg-cream);
  padding: 4px;
  border-radius: {RADIUS['sm']};
  border: 1px solid var(--sg-border);
  width: fit-content;
}}
[data-testid="stTabs"] button[data-baseweb="tab"] {{
  border-radius: 8px;
  padding: 0.4rem 0.95rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--sg-muted);
  background: transparent;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
  background: var(--sg-surface);
  color: var(--sg-text);
  box-shadow: 0 1px 2px rgba(41, 38, 58, 0.06);
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none; }}

/* ---------- Tables ---------- */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['md']};
  overflow: hidden;
  background: var(--sg-surface);
}}

/* ---------- Expander ---------- */
[data-testid="stExpander"] {{
  background: var(--sg-surface);
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['md']};
}}
[data-testid="stExpander"] summary {{
  font-weight: 600;
  font-size: 0.88rem;
}}

/* ---------- Alerts ---------- */
[data-testid="stAlert"] {{
  border-radius: {RADIUS['md']};
  border: 1px solid var(--sg-border);
}}

/* ---------- File uploader ---------- */
[data-testid="stFileUploaderDropzone"] {{
  background: var(--sg-surface);
  border: 1px dashed var(--sg-accent);
  border-radius: {RADIUS['md']};
}}

/* ---------- Charts ---------- */
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{
  background: var(--sg-surface);
  border: 1px solid var(--sg-border);
  border-radius: {RADIUS['md']};
  padding: 0.6rem;
}}

/* ---------- Sidebar nav ---------- */
[data-testid="stSidebar"] .stButton > button {{
  justify-content: flex-start;
  text-align: left;
  padding: 0.5rem 0.8rem;
  font-size: 0.87rem;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
  background: var(--sg-accent);
  border-color: var(--sg-accent);
  color: #3A2A1E;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
  background: var(--sg-accent-hover);
  border-color: var(--sg-accent-hover);
  color: #3A2A1E;
}}

/* ---------- Utility ---------- */
.sg-divider {{
  height: 1px;
  background: var(--sg-border);
  margin: 1.1rem 0;
}}
.sg-muted {{ color: var(--sg-muted); font-size: 0.82rem; }}
.sg-mono {{
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 0.82rem;
}}
.sg-scroll {{ max-height: 320px; overflow-y: auto; }}

@media (max-width: 900px) {{
  .block-container {{ padding: 1rem 1rem 2rem 1rem; }}
  .sg-page-title {{ font-size: 1.45rem; }}
}}
</style>
"""


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def brand() -> str:
    return """
<div style="display:flex;align-items:center;gap:11px;padding:0 0 4px 2px;">
  <div style="width:38px;height:38px;border-radius:12px;background:#F4B98F;
              display:flex;align-items:center;justify-content:center;
              font-weight:700;color:#3A2A1E;font-size:1.05rem;">SG</div>
  <div>
    <div style="font-weight:700;font-size:1.02rem;line-height:1.2;">SalesGenie</div>
    <div style="font-size:0.72rem;color:#777487;letter-spacing:0.04em;">Sales intelligence</div>
  </div>
</div>
"""


def page_head(eyebrow: str, title: str, description: str) -> None:
    import streamlit as st

    st.markdown(
        f"""
<div style="margin:0 0 1.1rem 0;">
  <div class="sg-eyebrow">{esc(eyebrow)}</div>
  <h1 class="sg-page-title">{esc(title)}</h1>
  <p class="sg-page-sub">{esc(description)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    import streamlit as st

    sub = f'<p class="sg-section-sub">{esc(subtitle)}</p>' if subtitle else ""
    st.markdown(
        f'<div style="margin:0.2rem 0 0.7rem 0;">'
        f'<p class="sg-section-title">{esc(title)}</p>{sub}</div>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value, meta: str = "", tone: str = "neutral") -> str:
    color = TONE.get(tone, PALETTE["text"])
    meta_html = f'<div class="sg-kpi-meta">{esc(meta)}</div>' if meta else ""
    text = str(value)
    size = "1.9rem" if len(text) <= 8 else "1.45rem"
    return (
        '<div class="sg-kpi">'
        f'<div class="sg-kpi-label">{esc(label)}</div>'
        f'<div class="sg-kpi-value" style="color:{color};font-size:{size};">{esc(value)}</div>'
        f"{meta_html}</div>"
    )


def kpi_row(cards: list[str]) -> str:
    """Lay KPI cards out in one responsive row.

    Streamlit columns are equal-width and become cramped at laptop widths, so
    the row is a wrapping flex container instead: cards keep a readable minimum
    width and wrap onto a second line on narrow viewports.
    """
    return (
        '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:0.4rem;">'
        + "".join(
            f'<div style="flex:1 1 168px;min-width:150px;display:flex;">{card}</div>'
            for card in cards
        )
        + "</div>"
    )


def badge(text: str, tone: str = "neutral") -> str:
    color = TONE.get(tone, PALETTE["text"])
    background = TONE_BG.get(tone, "#F6F1EC")
    return (
        f'<span class="sg-badge" style="color:{color};background:{background};">'
        f"{esc(text)}</span>"
    )


def status_dot(text: str, tone: str = "success") -> str:
    color = TONE.get(tone, PALETTE["success"])
    return (
        '<span style="display:inline-flex;align-items:center;gap:7px;'
        'font-size:0.8rem;font-weight:600;">'
        f'<span class="sg-dot" style="background:{color};"></span>'
        f'<span style="color:{color};">{esc(text)}</span></span>'
    )


def card(title: str, body: str, tone: str = "neutral", footer: str = "") -> str:
    color = TONE.get(tone, PALETTE["text"])
    footer_html = f'<div class="sg-muted" style="margin-top:0.6rem;">{footer}</div>' if footer else ""
    return (
        '<div class="sg-card">'
        f'<div style="font-size:0.78rem;font-weight:650;letter-spacing:0.05em;'
        f'text-transform:uppercase;color:{color};margin-bottom:0.4rem;">{esc(title)}</div>'
        f'<div style="font-size:0.9rem;line-height:1.6;">{body}</div>'
        f"{footer_html}</div>"
    )


def empty_state(title: str, body: str, hint: str = "") -> None:
    import streamlit as st

    hint_html = (
        f'<div style="font-size:0.8rem;color:#777487;margin-top:0.5rem;">{esc(hint)}</div>'
        if hint
        else ""
    )
    st.markdown(
        '<div class="sg-card" style="text-align:center;padding:2.2rem 1.5rem;">'
        '<div style="width:44px;height:44px;border-radius:14px;background:#FFF0E2;'
        'margin:0 auto 0.8rem auto;display:flex;align-items:center;justify-content:center;'
        'font-weight:700;color:#B4652F;">—</div>'
        f'<div style="font-weight:650;font-size:0.98rem;">{esc(title)}</div>'
        f'<div style="font-size:0.86rem;color:#777487;margin-top:0.35rem;max-width:46ch;'
        f'margin-left:auto;margin-right:auto;">{esc(body)}</div>'
        f"{hint_html}</div>",
        unsafe_allow_html=True,
    )


def error_note(message: str) -> None:
    import streamlit as st

    st.markdown(
        f'<div class="sg-card" style="border-left:3px solid #C45454;">'
        f'<div style="font-weight:650;color:#C45454;font-size:0.86rem;">'
        f"Action could not be completed</div>"
        f'<div style="font-size:0.85rem;margin-top:0.25rem;">{esc(message)}</div></div>',
        unsafe_allow_html=True,
    )


def success_note(message: str) -> None:
    import streamlit as st

    st.markdown(
        f'<div class="sg-card" style="border-left:3px solid #398568;">'
        f'<div style="font-size:0.86rem;">{esc(message)}</div></div>',
        unsafe_allow_html=True,
    )


def warning_note(message: str, title: str = "Nothing was changed") -> None:
    import streamlit as st

    st.markdown(
        f'<div class="sg-card" style="border-left:3px solid #B77935;">'
        f'<div style="font-weight:650;color:#B77935;font-size:0.86rem;">{esc(title)}</div>'
        f'<div style="font-size:0.85rem;margin-top:0.25rem;">{esc(message)}</div></div>',
        unsafe_allow_html=True,
    )


def meta_row(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div style="min-width:120px;"><div class="sg-kpi-label">{esc(label)}</div>'
        f'<div style="font-size:0.88rem;font-weight:600;margin-top:2px;">{esc(value)}</div></div>'
        for label, value in items
    )
    return f'<div style="display:flex;gap:1.8rem;flex-wrap:wrap;">{cells}</div>'
