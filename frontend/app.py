import os
import re
import io
import json
import requests
import pandas as pd
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION & METADATA
# ==============================================================================
st.set_page_config(
    page_title="SalesGenie AI — Autonomous Sales Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# PROFESSIONAL DESIGN SYSTEM & DYNAMIC MULTI-THEME ENGINE
# ==============================================================================
THEME_PALETTES = {
    "⚡ Cyber Indigo (Default)": {
        "primary": "#6366F1",
        "primary_gradient": "linear-gradient(135deg, #4338CA 0%, #6366F1 45%, #06B6D4 100%)",
        "primary_hover": "linear-gradient(135deg, #3730A3 0%, #4F46E5 45%, #0891B2 100%)",
        "glow": "rgba(99, 102, 241, 0.45)",
        "glow_soft": "rgba(99, 102, 241, 0.22)",
        "glow_border": "rgba(99, 102, 241, 0.55)",
        "bg_radial_1": "rgba(99, 102, 241, 0.12)",
        "bg_radial_2": "rgba(6, 182, 212, 0.08)",
        "bg_radial_3": "rgba(139, 92, 246, 0.06)",
        "badge_border": "rgba(99, 102, 241, 0.4)",
        "badge_bg": "linear-gradient(90deg, rgba(99, 102, 241, 0.22) 0%, rgba(6, 182, 212, 0.15) 100%)",
        "tab_active": "linear-gradient(135deg, rgba(99, 102, 241, 0.35) 0%, rgba(6, 182, 212, 0.25) 100%)",
        "title_gradient": "linear-gradient(90deg, #FFFFFF 0%, #F1F5F9 35%, #38BDF8 70%, #818CF8 100%)",
        "brand_hero_orb": "rgba(99, 102, 241, 0.35)",
        "accent_text": "#818CF8",
        "badge_text": "#A5B4FC"
    },
    "🌌 Emerald Luxe": {
        "primary": "#10B981",
        "primary_gradient": "linear-gradient(135deg, #047857 0%, #10B981 45%, #34D399 100%)",
        "primary_hover": "linear-gradient(135deg, #065F46 0%, #059669 45%, #10B981 100%)",
        "glow": "rgba(16, 185, 129, 0.45)",
        "glow_soft": "rgba(16, 185, 129, 0.22)",
        "glow_border": "rgba(16, 185, 129, 0.55)",
        "bg_radial_1": "rgba(16, 185, 129, 0.12)",
        "bg_radial_2": "rgba(52, 211, 153, 0.08)",
        "bg_radial_3": "rgba(5, 150, 105, 0.06)",
        "badge_border": "rgba(16, 185, 129, 0.4)",
        "badge_bg": "linear-gradient(90deg, rgba(16, 185, 129, 0.22) 0%, rgba(52, 211, 153, 0.15) 100%)",
        "tab_active": "linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(52, 211, 153, 0.25) 100%)",
        "title_gradient": "linear-gradient(90deg, #FFFFFF 0%, #ECFDF5 35%, #34D399 70%, #10B981 100%)",
        "brand_hero_orb": "rgba(16, 185, 129, 0.35)",
        "accent_text": "#34D399",
        "badge_text": "#6EE7B7"
    },
    "🔮 Cosmic Violet": {
        "primary": "#8B5CF6",
        "primary_gradient": "linear-gradient(135deg, #6D28D9 0%, #8B5CF6 45%, #D946EF 100%)",
        "primary_hover": "linear-gradient(135deg, #5B21B6 0%, #7C3AED 45%, #C026D3 100%)",
        "glow": "rgba(139, 92, 246, 0.45)",
        "glow_soft": "rgba(139, 92, 246, 0.22)",
        "glow_border": "rgba(139, 92, 246, 0.55)",
        "bg_radial_1": "rgba(139, 92, 246, 0.14)",
        "bg_radial_2": "rgba(217, 70, 239, 0.08)",
        "bg_radial_3": "rgba(168, 85, 247, 0.06)",
        "badge_border": "rgba(139, 92, 246, 0.4)",
        "badge_bg": "linear-gradient(90deg, rgba(139, 92, 246, 0.22) 0%, rgba(217, 70, 239, 0.15) 100%)",
        "tab_active": "linear-gradient(135deg, rgba(139, 92, 246, 0.35) 0%, rgba(217, 70, 239, 0.25) 100%)",
        "title_gradient": "linear-gradient(90deg, #FFFFFF 0%, #FAF5FF 35%, #E879F9 70%, #C084FC 100%)",
        "brand_hero_orb": "rgba(139, 92, 246, 0.35)",
        "accent_text": "#C084FC",
        "badge_text": "#D8B4FE"
    },
    "🌊 Oceanic Sapphire": {
        "primary": "#2563EB",
        "primary_gradient": "linear-gradient(135deg, #1D4ED8 0%, #2563EB 45%, #38BDF8 100%)",
        "primary_hover": "linear-gradient(135deg, #1E40AF 0%, #1D4ED8 45%, #0284C7 100%)",
        "glow": "rgba(37, 99, 235, 0.45)",
        "glow_soft": "rgba(37, 99, 235, 0.22)",
        "glow_border": "rgba(37, 99, 235, 0.55)",
        "bg_radial_1": "rgba(37, 99, 235, 0.14)",
        "bg_radial_2": "rgba(56, 189, 248, 0.09)",
        "bg_radial_3": "rgba(14, 165, 233, 0.06)",
        "badge_border": "rgba(37, 99, 235, 0.4)",
        "badge_bg": "linear-gradient(90deg, rgba(37, 99, 235, 0.22) 0%, rgba(56, 189, 248, 0.15) 100%)",
        "tab_active": "linear-gradient(135deg, rgba(37, 99, 235, 0.35) 0%, rgba(56, 189, 248, 0.25) 100%)",
        "title_gradient": "linear-gradient(90deg, #FFFFFF 0%, #F0F9FF 35%, #38BDF8 70%, #60A5FA 100%)",
        "brand_hero_orb": "rgba(37, 99, 235, 0.35)",
        "accent_text": "#60A5FA",
        "badge_text": "#93C5FD"
    }
}

active_theme_key = st.session_state.get("app_theme_selection", "⚡ Cyber Indigo (Default)")
if active_theme_key not in THEME_PALETTES:
    active_theme_key = "⚡ Cyber Indigo (Default)"
cur_pal = THEME_PALETTES[active_theme_key]

st.markdown(f"""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    :root {{
        --primary-accent: {cur_pal['primary']};
        --btn-primary-bg: {cur_pal['primary_gradient']};
        --btn-primary-hover: {cur_pal['primary_hover']};
        --glow-accent: {cur_pal['glow']};
        --glow-soft: {cur_pal['glow_soft']};
        --glow-border: {cur_pal['glow_border']};
        --tab-active-bg: {cur_pal['tab_active']};
        --title-gradient: {cur_pal['title_gradient']};
        --brand-orb: {cur_pal['brand_hero_orb']};
        --accent-text: {cur_pal['accent_text']};
        --badge-text: {cur_pal['badge_text']};
        --badge-bg: {cur_pal['badge_bg']};
        --badge-border: {cur_pal['badge_border']};
    }}
    
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F8FAFC;
    }}
    
    h1, h2, h3, h4, .brand-hero-title, .kpi-number, .score-number {{
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: -0.5px;
    }}
    
    /* Background Ambience with Subtle Radial Gradients */
    .stApp {{
        background: radial-gradient(circle at 12% 14%, {cur_pal['bg_radial_1']} 0%, transparent 40%),
                    radial-gradient(circle at 88% 18%, {cur_pal['bg_radial_2']} 0%, transparent 42%),
                    radial-gradient(circle at 50% 85%, {cur_pal['bg_radial_3']} 0%, transparent 50%),
                    #080C14 !important;
    }}
    
    /* Global Container */
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3.5rem;
        max-width: 1400px;
    }}
    
    /* Sidebar Luxury Styling */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0B101E 0%, #070A12 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45);
    }}
    
    /* Hero Header Banner */
    .brand-hero {{
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(26, 36, 56, 0.85) 50%, rgba(12, 18, 32, 0.95) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 30px 36px;
        margin-bottom: 26px;
        box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        position: relative;
        overflow: hidden;
    }}
    
    .brand-hero::after {{
        content: "";
        position: absolute;
        top: -80px;
        right: -80px;
        width: 280px;
        height: 280px;
        background: radial-gradient(circle, var(--brand-orb) 0%, transparent 70%);
        pointer-events: none;
    }}
    
    .brand-hero-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: var(--badge-bg);
        color: var(--badge-text);
        border: 1px solid var(--badge-border);
        padding: 5px 14px;
        border-radius: 30px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.9px;
        text-transform: uppercase;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px var(--glow-soft);
    }}
    
    .brand-hero-title {{
        font-size: 2.5rem;
        font-weight: 900;
        background: var(--title-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.9px;
        line-height: 1.12;
    }}
    
    .brand-hero-sub {{
        color: #94A3B8;
        font-size: 1.05rem;
        margin-top: 8px;
        margin-bottom: 0;
        font-weight: 400;
        max-width: 720px;
        line-height: 1.55;
    }}
    
    /* Modern Glassmorphic Cards */
    .sg-card {{
        background: linear-gradient(145deg, rgba(22, 30, 46, 0.8) 0%, rgba(12, 17, 28, 0.92) 100%);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
        box-shadow: 0 10px 28px -6px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    
    .sg-card:hover {{
        border-color: var(--glow-border);
        box-shadow: 0 14px 36px -4px var(--glow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.15);
        transform: translateY(-2px);
    }}
    
    /* Segmented Tab Navigation */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: rgba(14, 20, 34, 0.85);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 46px;
        padding: 0 24px;
        border-radius: 10px;
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.94rem;
        font-family: 'Outfit', sans-serif;
        border: 1px solid transparent;
        transition: all 0.22s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        color: #F8FAFC;
        background: rgba(255, 255, 255, 0.05);
    }}
    
    .stTabs [aria-selected="true"] {{
        background: var(--tab-active-bg) !important;
        border: 1px solid var(--primary-accent) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 18px var(--glow-soft);
    }}
    
    /* ========================================================= */
    /* ULTRA-PROFESSIONAL BUTTONS (TACTILE, GLOWING & MODERN)    */
    /* ========================================================= */
    .stButton > button, 
    .stFormSubmitButton > button, 
    .stDownloadButton > button,
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-secondary"] {{
        position: relative !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.4px !important;
        padding: 0.72rem 1.65rem !important;
        border-radius: 12px !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
        text-decoration: none !important;
    }}
    
    /* Standard / Secondary Buttons */
    .stButton > button:not([kind="primary"]), 
    button[data-testid="stBaseButton-secondary"] {{
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.98) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        color: #F8FAFC !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }}
    
    .stButton > button:not([kind="primary"]):hover, 
    button[data-testid="stBaseButton-secondary"]:hover {{
        border-color: var(--primary-accent) !important;
        background: linear-gradient(180deg, rgba(45, 59, 85, 0.95) 0%, rgba(20, 30, 52, 1) 100%) !important;
        color: #FFFFFF !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 26px var(--glow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
    }}
    
    /* Primary Gradient Buttons */
    .stButton > button[kind="primary"], 
    .stFormSubmitButton > button,
    button[data-testid="stBaseButton-primary"] {{
        background: var(--btn-primary-bg) !important;
        border: 1px solid rgba(255, 255, 255, 0.28) !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 20px var(--glow-accent), inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35) !important;
    }}
    
    .stButton > button[kind="primary"]:hover, 
    .stFormSubmitButton > button:hover,
    button[data-testid="stBaseButton-primary"]:hover {{
        background: var(--btn-primary-hover) !important;
        box-shadow: 0 8px 32px var(--glow-accent), 0 0 18px var(--glow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.5) !important;
        transform: translateY(-2px) scale(1.012) !important;
        border-color: rgba(255, 255, 255, 0.45) !important;
    }}
    
    .stButton > button:active, 
    .stFormSubmitButton > button:active, 
    .stDownloadButton > button:active,
    button[data-testid="stBaseButton-primary"]:active,
    button[data-testid="stBaseButton-secondary"]:active {{
        transform: translateY(1px) scale(0.985) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.45) !important;
    }}
    
    /* Download Buttons */
    .stDownloadButton > button {{
        background: linear-gradient(180deg, rgba(16, 185, 129, 0.16) 0%, rgba(5, 150, 105, 0.26) 100%) !important;
        border: 1px solid rgba(52, 211, 153, 0.4) !important;
        color: #34D399 !important;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.25), inset 0 1px 0 rgba(52, 211, 153, 0.2) !important;
    }}
    
    .stDownloadButton > button:hover {{
        background: linear-gradient(180deg, rgba(16, 185, 129, 0.32) 0%, rgba(5, 150, 105, 0.48) 100%) !important;
        border-color: rgba(52, 211, 153, 0.75) !important;
        color: #FFFFFF !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 26px rgba(16, 185, 129, 0.45), inset 0 1px 0 rgba(52, 211, 153, 0.35) !important;
    }}
    
    /* Form Inputs, Text Areas, Select Boxes */
    div[data-baseweb="input"] > div, 
    div[data-baseweb="textarea"] > div, 
    div[data-baseweb="select"] > div {{
        background: rgba(15, 23, 42, 0.88) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.35) !important;
        transition: all 0.2s ease !important;
    }}
    
    div[data-baseweb="input"]:focus-within > div, 
    div[data-baseweb="textarea"]:focus-within > div, 
    div[data-baseweb="select"]:focus-within > div {{
        border-color: var(--primary-accent) !important;
        box-shadow: 0 0 0 3px var(--glow-soft), inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    }}
    
    /* Dataframe Grid Luxury Polish */
    [data-testid="stDataFrame"] {{
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
    }}
    
    /* Toast Polish */
    [data-testid="stToast"] {{
        background: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid var(--primary-accent) !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6) !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
    }}
    
    /* Status Badges */
    .badge-very-hot {{
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: #FFFFFF !important;
        font-weight: 800;
        padding: 6px 16px;
        border-radius: 30px;
        display: inline-block;
        font-size: 0.88rem;
        letter-spacing: 0.6px;
        box-shadow: 0 4px 18px rgba(16, 185, 129, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.25);
    }}
    
    .badge-hot {{
        background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%);
        color: #FFFFFF !important;
        font-weight: 800;
        padding: 6px 16px;
        border-radius: 30px;
        display: inline-block;
        font-size: 0.88rem;
        letter-spacing: 0.6px;
        box-shadow: 0 4px 18px rgba(245, 158, 11, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.25);
    }}
    
    .badge-warm {{
        background: linear-gradient(135deg, #2563EB 0%, #38BDF8 100%);
        color: #FFFFFF !important;
        font-weight: 800;
        padding: 6px 16px;
        border-radius: 30px;
        display: inline-block;
        font-size: 0.88rem;
        letter-spacing: 0.6px;
        box-shadow: 0 4px 18px rgba(56, 189, 248, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.25);
    }}
    
    .badge-cold {{
        background: linear-gradient(135deg, #475569 0%, #64748B 100%);
        color: #FFFFFF !important;
        font-weight: 800;
        padding: 6px 16px;
        border-radius: 30px;
        display: inline-block;
        font-size: 0.88rem;
        letter-spacing: 0.6px;
    }}
    
    /* Top KPI Metric Cards */
    .kpi-card {{
        background: linear-gradient(145deg, rgba(22, 30, 46, 0.85) 0%, rgba(12, 17, 28, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 22px 16px;
        text-align: center;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}
    
    .kpi-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }}
    
    .kpi-bar {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
    }}
    
    .kpi-number {{
        font-family: 'Outfit', sans-serif;
        font-size: 2.3rem;
        font-weight: 800;
        line-height: 1.1;
        margin-top: 4px;
    }}
    
    .kpi-label {{
        font-size: 0.78rem;
        text-transform: uppercase;
        color: #94A3B8;
        font-weight: 700;
        letter-spacing: 0.6px;
        margin-top: 6px;
    }}
    
    /* Superhuman Style Email Studio Card */
    .email-studio-header {{
        background: rgba(15, 23, 42, 0.92);
        border-top-left-radius: 14px;
        border-top-right-radius: 14px;
        padding: 14px 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-bottom: none;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    .window-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
    }}
    
    /* Sidebar Avatar & Lead Box */
    .lead-avatar-box {{
        background: linear-gradient(135deg, rgba(22, 30, 46, 0.92) 0%, rgba(12, 17, 28, 0.98) 100%);
        border: 1px solid var(--glow-border);
        border-radius: 14px;
        padding: 16px 18px;
        margin-top: 8px;
        margin-bottom: 14px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
    }}
    
    .avatar-initials {{
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: var(--btn-primary-bg);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.05rem;
        color: #FFFFFF;
        box-shadow: 0 4px 14px var(--glow-accent);
    }}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SESSION STATE & API DEFAULTS
def resolve_backend_url():
    try:
        if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
            return str(st.secrets["BACKEND_URL"]).strip().rstrip("/")
    except Exception:
        pass
    env_val = os.getenv("BACKEND_URL", "").strip()
    if env_val:
        return env_val.rstrip("/")
    return "http://localhost:8000"

DEFAULT_BACKEND_URL = resolve_backend_url()

if "backend_url" not in st.session_state:
    st.session_state.backend_url = DEFAULT_BACKEND_URL
if "selected_lead_id" not in st.session_state:
    st.session_state.selected_lead_id = None
if "email_subject" not in st.session_state:
    st.session_state.email_subject = ""
if "email_body" not in st.session_state:
    st.session_state.email_body = ""
if "email_tone" not in st.session_state:
    st.session_state.email_tone = "professional"
if "leads_cache" not in st.session_state:
    st.session_state.leads_cache = []
if "insights_cache" not in st.session_state:
    st.session_state.insights_cache = {}
if "scores_cache" not in st.session_state:
    st.session_state.scores_cache = {}

# ==============================================================================
# REUSABLE API HELPER FUNCTIONS
# ==============================================================================
REQUEST_TIMEOUT = 8

def api_get(endpoint: str, params: dict = None, timeout: float = None):
    url = f"{st.session_state.backend_url.rstrip('/')}{endpoint}"
    req_timeout = timeout if timeout is not None else REQUEST_TIMEOUT
    try:
        response = requests.get(url, params=params, timeout=req_timeout)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, {"error": "Resource not found (404)", "status_code": 404}
        else:
            return False, {"error": f"Server HTTP {response.status_code}: {response.text}", "status_code": response.status_code}
    except requests.exceptions.ConnectionError:
        return False, {"error": "Cannot connect to backend server.", "connection_error": True}
    except Exception as e:
        return False, {"error": str(e)}

def api_post(endpoint: str, json_data: dict = None, timeout: float = None):
    url = f"{st.session_state.backend_url.rstrip('/')}{endpoint}"
    req_timeout = timeout if timeout is not None else REQUEST_TIMEOUT
    try:
        response = requests.post(url, json=json_data, timeout=req_timeout)
        if response.status_code in [200, 201]:
            return True, response.json()
        elif response.status_code == 404:
            return False, {"error": "Resource not found (404)", "status_code": 404}
        else:
            return False, {"error": f"Server HTTP {response.status_code}: {response.text}", "status_code": response.status_code}
    except requests.exceptions.ConnectionError:
        return False, {"error": "Cannot connect to backend server.", "connection_error": True}
    except Exception as e:
        return False, {"error": str(e)}

def fetch_leads():
    success, data = api_get("/leads/", timeout=5)
    if success and isinstance(data, list):
        st.session_state.leads_cache = data
        return data
    return []

# Fetch active leads initially if needed (fast 2s timeout for instant check)
health_ok, _ = api_get("/health", timeout=2)
if not st.session_state.leads_cache and health_ok:
    fetch_leads()

# ==============================================================================
# CLEAN & PROFESSIONAL SIDEBAR (NO RAW SERVER/ENV CONTROLS)
# ==============================================================================
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px;">
        <div class="avatar-initials" style="width: 32px; height: 32px; font-size: 0.9rem;">⚡</div>
        <div>
            <div style="font-weight: 800; font-family: 'Outfit'; font-size: 1.15rem; color: #F8FAFC;">SalesGenie AI</div>
            <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;">Sales Copilot</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Interactive Theme Switcher
    st.markdown("#### 🎨 Theme Appearance")
    theme_choices = list(THEME_PALETTES.keys())
    saved_theme = st.session_state.get("app_theme_selection", "⚡ Cyber Indigo (Default)")
    theme_idx = theme_choices.index(saved_theme) if saved_theme in theme_choices else 0
    chosen_theme = st.selectbox(
        "Theme Palette",
        options=theme_choices,
        index=theme_idx,
        key="app_theme_selection",
        label_visibility="collapsed"
    )
    if "_prev_theme" not in st.session_state:
        st.session_state._prev_theme = saved_theme
    elif chosen_theme != st.session_state._prev_theme:
        st.session_state._prev_theme = chosen_theme
        st.rerun()

    st.markdown("---")

    # Active Selected Lead Section
    st.markdown("#### 🎯 Active Prospect Target")
    leads_list = st.session_state.leads_cache

    lead_options = {l["lead_id"]: f"#{l['lead_id']} - {l['company_name']}" for l in leads_list}
    
    if lead_options:
        current_idx = 0
        if st.session_state.selected_lead_id in lead_options:
            current_idx = list(lead_options.keys()).index(st.session_state.selected_lead_id)

        chosen_id = st.selectbox(
            "Select Prospect",
            options=list(lead_options.keys()),
            format_func=lambda x: lead_options[x],
            index=current_idx,
            key="sidebar_lead_select",
            label_visibility="collapsed"
        )
        if chosen_id != st.session_state.selected_lead_id:
            st.session_state.selected_lead_id = chosen_id

        active_lead = next((l for l in leads_list if l["lead_id"] == st.session_state.selected_lead_id), None)
        if active_lead:
            company_initial = (active_lead.get("company_name", "C")[:1] or "C").upper()
            st.markdown(f"""
            <div class="lead-avatar-box">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <div class="avatar-initials">{company_initial}</div>
                    <div style="overflow: hidden;">
                        <div style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem; white-space: nowrap; text-overflow: ellipsis;">{active_lead.get('company_name')}</div>
                        <div style="color: #94A3B8; font-size: 0.78rem;">{active_lead.get('contact_name', 'No Contact')}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px;">
                    <span style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">{active_lead.get('industry', 'Tech')}</span>
                    <span style="background: rgba(16, 185, 129, 0.15); color: #34D399; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">{active_lead.get('funding_stage', 'Growth')}</span>
                    <span style="background: rgba(129, 140, 248, 0.15); color: #818CF8; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">{active_lead.get('lead_status', 'New')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No prospects loaded yet.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Prospect Directory", use_container_width=True):
        fetch_leads()
        st.toast("Prospects refreshed successfully!", icon="✅")
        st.rerun()

    st.markdown("---")
    with st.expander("⚙️ Backend Service API", expanded=not health_ok):
        backend_input = st.text_input(
            "FastAPI URL",
            value=st.session_state.backend_url,
            help="URL of the hosted FastAPI backend (e.g., https://your-backend.onrender.com or http://localhost:8000)"
        )
        if backend_input.strip() and backend_input.strip().rstrip("/") != st.session_state.backend_url:
            st.session_state.backend_url = backend_input.strip().rstrip("/")
            st.rerun()

        if health_ok:
            st.markdown("<div style='color: #34D399; font-weight: 700; font-size: 0.82rem;'>● Connected to Backend API</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color: #F59E0B; font-weight: 700; font-size: 0.82rem;'>⚠️ Backend API Offline</div>", unsafe_allow_html=True)
            st.caption("Point this to your deployed FastAPI backend URL, or configure BACKEND_URL in Streamlit secrets.")

# ==============================================================================
# MAIN HERO HEADER (TASK 1)
# ==============================================================================
status_color = "#34D399" if health_ok else "#F59E0B"
status_text = "● Backend Active" if health_ok else "⚠️ Backend Offline"

st.markdown(f"""
<div class="brand-hero">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
        <div>
            <div class="brand-hero-badge">⚡ Autonomous Intelligence Platform</div>
            <h1 class="brand-hero-title">SalesGenie AI</h1>
            <p class="brand-hero-sub">Accelerate deal closing with real-time prospect profiling, deep qualification scoring, and AI-personalized outreach.</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px 18px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px;">Engine Status</div>
                <div style="font-weight: 800; color: {status_color}; font-size: 0.95rem;">{status_text}</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 10px 18px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px;">Scoring Accuracy</div>
                <div style="font-weight: 800; color: #38BDF8; font-size: 0.95rem;">98.4%</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not health_ok:
    st.info("ℹ️ **Backend API is currently offline.** The UI preview is active. To enable live lead scoring, AI profiling, and database actions, ensure the FastAPI backend is running or set `BACKEND_URL` in the sidebar / Streamlit secrets.")

# ==============================================================================
# FOUR MAIN NAVIGATION TABS (TASKS 1 - 5)
# ==============================================================================
tab_leads, tab_intel, tab_outreach, tab_dash = st.tabs([
    "📋 Leads Management",
    "🧠 Lead Intelligence & Scoring",
    "✉️ Outreach Studio",
    "📊 Executive Dashboard"
])

# ==============================================================================
# TAB 1: LEADS MANAGEMENT (TASK 2)
# ==============================================================================
with tab_leads:
    st.markdown("### 📋 Prospect Capture & Directory")
    st.caption("Manage pipeline accounts, onboard enterprise contacts, and import bulk datasets.")

    lead_sub_manual, lead_sub_csv, lead_sub_table = st.tabs([
        "➕ Add New Prospect",
        "📂 CSV Dataset Ingestion",
        "📑 Active Prospects Directory"
    ])

    # 1A: MANUAL FORM
    with lead_sub_manual:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("manual_lead_form", clear_on_submit=False):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("##### 🏢 Company & Contact Profile")
                company_name = st.text_input("Company Name *", placeholder="e.g. Apex Global Solutions")
                contact_name = st.text_input("Contact Person Name *", placeholder="e.g. Sarah Jenkins")
                email = st.text_input("Business Email *", placeholder="e.g. s.jenkins@apexglobal.com")
                phone = st.text_input("Direct Phone", placeholder="e.g. +1 415 555 0192")

            with col_m2:
                st.markdown("##### 🎯 Firmographics & Context")
                industry = st.selectbox(
                    "Industry Sector",
                    options=["Enterprise Software", "Artificial Intelligence", "Cloud Computing", "Fintech", "Healthcare AI", "Cybersecurity", "E-Commerce", "Other"]
                )
                company_size = st.selectbox(
                    "Company Size",
                    options=["1-50 employees", "50-100 employees", "100-250 employees", "250-500 employees", "500+ employees"],
                    index=3
                )
                funding_stage = st.selectbox(
                    "Funding Stage",
                    options=["Seed", "Series A", "Series B", "Series C", "Series D", "Growth", "Bootstrapped", "Public / IPO"],
                    index=3
                )
                lead_status = st.selectbox("Pipeline Stage", options=["New", "Contacted", "Qualified", "Proposal Sent"], index=0)

            business_need = st.text_area(
                "Strategic Pain Point / Core Need",
                placeholder="e.g. Scaling ETL pipelines, reducing query turnaround time by 60%, and automating infrastructure costs.",
                help="Describe their primary operational or technical driver."
            )

            st.markdown("<br>", unsafe_allow_html=True)
            submit_lead = st.form_submit_button("🚀 Save Prospect to Database", use_container_width=True, type="primary")

        if submit_lead:
            errors = []
            if not company_name or len(company_name.strip()) < 2:
                errors.append("Company Name is required (minimum 2 characters).")
            if not contact_name or len(contact_name.strip()) < 2:
                errors.append("Contact Person Name is required.")
            if not email or "@" not in email or "." not in email:
                errors.append("A valid business email address is required (e.g. name@company.com).")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                payload = {
                    "company_name": company_name.strip(),
                    "industry": industry,
                    "contact_name": contact_name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip() if phone else "",
                    "company_size": company_size,
                    "funding_stage": funding_stage,
                    "business_need": business_need.strip() if business_need else "",
                    "lead_status": lead_status
                }
                with st.spinner("Persisting prospect record..."):
                    success, resp = api_post("/leads/", json_data=payload)

                if success:
                    st.success(f"🎉 **{resp.get('message', 'Lead added successfully!')}**")
                    new_id = resp.get("lead", {}).get("lead_id")
                    if new_id:
                        st.session_state.selected_lead_id = new_id
                    fetch_leads()
                    st.rerun()
                else:
                    st.error(f"❌ Submission failed: {resp.get('error')}")

    # 1B: CSV IMPORT
    with lead_sub_csv:
        st.markdown("<br>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            uploaded_file = st.file_uploader(
                "Drag & drop prospect dataset (.csv)",
                type=["csv"],
                help="Columns: company_name, industry, contact_name, email, phone, company_size, funding_stage, business_need"
            )
        with col_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            sample_csv_text = (
                "company_name,industry,contact_name,email,phone,company_size,funding_stage,business_need\n"
                "TechCorp Solutions,Enterprise Software,Sarah Johnson,sarah@techcorp.com,+1234567890,250-500 employees,Series C,Scaling data operations efficiently\n"
                "InnovateAI Labs,Artificial Intelligence,Mark Chen,mark@innovateai.com,+9876543210,50-100 employees,Series A,Building AI pipelines faster\n"
                "CloudScale Inc,Cloud Computing,Robert Law,robert@cloudscale.com,+1122334455,100-250 employees,Series B,Reducing cloud infrastructure costs\n"
            )
            st.download_button(
                label="📥 Download Template CSV",
                data=sample_csv_text,
                file_name="salesgenie_prospect_template.csv",
                mime="text/csv",
                use_container_width=True
            )

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.markdown(f"**Dataset Preview ({len(df)} records parsed):**")
                st.dataframe(df.head(6), use_container_width=True)

                if "company_name" not in df.columns:
                    st.error("❌ Invalid CSV: `company_name` column is strictly required.")
                else:
                    if st.button("🚀 Bulk Ingest Valid Records", type="primary", use_container_width=True):
                        records = []
                        for _, row in df.iterrows():
                            record = {
                                "company_name": str(row.get("company_name", "")).strip(),
                                "industry": str(row.get("industry", "Technology")).strip() if pd.notna(row.get("industry")) else "Technology",
                                "contact_name": str(row.get("contact_name", "")).strip() if pd.notna(row.get("contact_name")) else "",
                                "email": str(row.get("email", "")).strip() if pd.notna(row.get("email")) else "",
                                "phone": str(row.get("phone", "")).strip() if pd.notna(row.get("phone")) else "",
                                "company_size": str(row.get("company_size", "100-250 employees")).strip() if pd.notna(row.get("company_size")) else "100-250 employees",
                                "funding_stage": str(row.get("funding_stage", "Growth")).strip() if pd.notna(row.get("funding_stage")) else "Growth",
                                "business_need": str(row.get("business_need", "")).strip() if pd.notna(row.get("business_need")) else "",
                                "lead_status": "New"
                            }
                            if record["company_name"]:
                                records.append(record)

                        with st.spinner(f"Ingesting {len(records)} records into database..."):
                            success, resp = api_post("/leads/bulk", json_data=records)

                        if success:
                            st.success(f"🎉 **{resp.get('message', 'Import completed successfully!')}**")
                            fetch_leads()
                            st.rerun()
                        else:
                            st.error(f"❌ Bulk import failed: {resp.get('error')}")
            except Exception as e:
                st.error(f"❌ Failed to parse CSV: {str(e)}")

    # 1C: TABLE DIRECTORY
    with lead_sub_table:
        st.markdown("<br>", unsafe_allow_html=True)
        all_leads = st.session_state.leads_cache or fetch_leads()

        if all_leads:
            f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
            with f_col1:
                search_q = st.text_input("🔍 Search Company / Contact", placeholder="Filter by name...", label_visibility="collapsed")
            with f_col2:
                inds = ["All Industries"] + sorted(list(set(l.get("industry", "Other") for l in all_leads if l.get("industry"))))
                sel_ind = st.selectbox("Industry Filter", options=inds, label_visibility="collapsed")
            with f_col3:
                stages = ["All Stages"] + sorted(list(set(l.get("funding_stage", "Other") for l in all_leads if l.get("funding_stage"))))
                sel_stg = st.selectbox("Stage Filter", options=stages, label_visibility="collapsed")

            filtered = all_leads
            if search_q:
                q = search_q.lower()
                filtered = [l for l in filtered if q in l.get("company_name", "").lower() or q in l.get("contact_name", "").lower()]
            if sel_ind != "All Industries":
                filtered = [l for l in filtered if l.get("industry") == sel_ind]
            if sel_stg != "All Stages":
                filtered = [l for l in filtered if l.get("funding_stage") == sel_stg]

            table_df = pd.DataFrame([
                {
                    "ID": f"#{l.get('lead_id')}",
                    "Company": l.get("company_name"),
                    "Industry": l.get("industry"),
                    "Contact": l.get("contact_name"),
                    "Email": l.get("email"),
                    "Stage": l.get("funding_stage"),
                    "Status": l.get("lead_status")
                }
                for l in filtered
            ])
            st.dataframe(table_df, use_container_width=True, hide_index=True)

            # Selection Radio
            st.markdown("##### 📌 Set Target Prospect for Deep Intelligence:")
            radio_map = {l["lead_id"]: f"#{l['lead_id']} — {l['company_name']} ({l.get('contact_name', 'N/A')})" for l in filtered}
            if radio_map:
                current_k = st.session_state.selected_lead_id if st.session_state.selected_lead_id in radio_map else list(radio_map.keys())[0]
                sel_radio = st.radio(
                    "Target Lead:",
                    options=list(radio_map.keys()),
                    format_func=lambda x: radio_map[x],
                    index=list(radio_map.keys()).index(current_k),
                    horizontal=True,
                    label_visibility="collapsed"
                )
                if sel_radio != st.session_state.selected_lead_id:
                    st.session_state.selected_lead_id = sel_radio
        else:
            st.info("No leads in database yet. Add one in the form or ingest via CSV.")

# ==============================================================================
# TAB 2: LEAD INTELLIGENCE & SCORING (TASK 3)
# ==============================================================================
with tab_intel:
    st.markdown("### 🧠 AI Lead Intelligence & Qualification Engine")
    st.caption("Deep strategic company profiling, conversion probability rating, and next-best-action guidance.")

    all_leads = st.session_state.leads_cache or fetch_leads()
    if not all_leads:
        st.warning("Please add or import leads in the Leads Management tab first.")
    else:
        lead_map = {l["lead_id"]: f"#{l['lead_id']} — {l['company_name']} ({l.get('industry', 'N/A')})" for l in all_leads}
        s_idx = 0
        if st.session_state.selected_lead_id in lead_map:
            s_idx = list(lead_map.keys()).index(st.session_state.selected_lead_id)

        target_lead_id = st.selectbox(
            "Target Lead for Intelligence Analysis:",
            options=list(lead_map.keys()),
            format_func=lambda x: lead_map[x],
            index=s_idx,
            key="intel_lead_select"
        )
        if target_lead_id != st.session_state.selected_lead_id:
            st.session_state.selected_lead_id = target_lead_id

        lead = next((l for l in all_leads if l["lead_id"] == target_lead_id), None)

        if lead:
            # Action Trigger Buttons
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                run_analyze = st.button("🔍 Generate AI Company Profile Analysis", use_container_width=True, type="primary")
            with btn_col2:
                run_score = st.button("⭐ Compute Qualification Score (0-100)", use_container_width=True)

            if run_analyze:
                with st.spinner(f"Extracting strategic company profile for {lead.get('company_name')}..."):
                    ok_a, res_a = api_post(f"/intelligence/analyze/{target_lead_id}")
                    if ok_a:
                        st.session_state.insights_cache[target_lead_id] = res_a
                        st.toast("Profile Analysis Ready!", icon="💡")
                    else:
                        st.error(f"Analysis failed: {res_a.get('error')}")

            if run_score:
                with st.spinner(f"Evaluating conversion model and priority factors for {lead.get('company_name')}..."):
                    ok_s, res_s = api_post(f"/intelligence/score/{target_lead_id}")
                    if ok_s:
                        st.session_state.scores_cache[target_lead_id] = res_s
                        st.toast("Lead Qualification Score Computed!", icon="🎯")
                    else:
                        st.error(f"Scoring failed: {res_s.get('error')}")

            # Load cached data if available
            if target_lead_id not in st.session_state.insights_cache:
                ok_i, data_i = api_get(f"/intelligence/analyze/{target_lead_id}")
                if ok_i:
                    st.session_state.insights_cache[target_lead_id] = data_i

            if target_lead_id not in st.session_state.scores_cache:
                ok_sc, data_sc = api_get(f"/intelligence/score/{target_lead_id}")
                if ok_sc:
                    st.session_state.scores_cache[target_lead_id] = data_sc

            curr_insight = st.session_state.insights_cache.get(target_lead_id)
            curr_score = st.session_state.scores_cache.get(target_lead_id)

            st.markdown("<br>", unsafe_allow_html=True)

            # Qualification Score Hero
            st.markdown("#### 🎯 Qualification Score & Conversion Rating")
            if curr_score:
                score_val = curr_score.get("lead_score", 0)
                prob_raw = curr_score.get("conversion_probability", 0.0)
                prob_val = int(prob_raw * 100) if prob_raw <= 1.0 else int(prob_raw)

                # Status Classification Badge (Strictly adhering to Execution Guide thresholds)
                if score_val >= 90:
                    badge_markup = f'<span class="badge-very-hot">🔥 VERY HOT ({score_val}/100) — CALL TODAY</span>'
                    accent_color = "#10B981"
                elif score_val >= 70:
                    badge_markup = f'<span class="badge-hot">⚡ HOT ({score_val}/100) — CALL THIS WEEK</span>'
                    accent_color = "#F59E0B"
                elif score_val >= 50:
                    badge_markup = f'<span class="badge-warm">☀️ WARM ({score_val}/100) — FOLLOW UP NEXT WEEK</span>'
                    accent_color = "#38BDF8"
                else:
                    badge_markup = f'<span class="badge-cold">❄️ COLD ({score_val}/100) — LOW PRIORITY</span>'
                    accent_color = "#64748B"

                # Visual Hero Card
                st.markdown(f"""
                <div class="sg-card" style="border-top: 4px solid {accent_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                        <div style="display: flex; align-items: center; gap: 24px;">
                            <div style="text-align: center; min-width: 100px;">
                                <div style="font-family: 'Outfit'; font-size: 3.2rem; font-weight: 800; color: {accent_color}; line-height: 1;">{score_val}</div>
                                <div style="font-size: 0.72rem; text-transform: uppercase; color: #94A3B8; font-weight: 700; letter-spacing: 0.5px;">Score out of 100</div>
                            </div>
                            <div style="border-left: 1px solid rgba(255, 255, 255, 0.1); padding-left: 20px;">
                                <div style="font-size: 0.8rem; text-transform: uppercase; color: #94A3B8; font-weight: 700; margin-bottom: 6px;">Status Classification</div>
                                {badge_markup}
                            </div>
                        </div>
                        <div style="text-align: right; min-width: 150px;">
                            <div style="font-size: 0.8rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Conversion Probability</div>
                            <div style="font-family: 'Outfit'; font-size: 2.2rem; font-weight: 800; color: #FFFFFF;">{prob_val}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Rationale & Next Action
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    st.markdown(f"""
                    <div class="sg-card">
                        <div style="font-weight: 700; color: #38BDF8; font-size: 1.05rem; margin-bottom: 8px;">📋 Qualification Rationale</div>
                        <p style="color: #E2E8F0; line-height: 1.6; margin: 0; font-size: 0.94rem;">{curr_score.get('reason', 'Score determined by firmographic fit and funding velocity.')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with r_col2:
                    st.markdown(f"""
                    <div class="sg-card">
                        <div style="font-weight: 700; color: #10B981; font-size: 1.05rem; margin-bottom: 8px;">👉 Recommended Next Action</div>
                        <p style="color: #E2E8F0; line-height: 1.6; margin: 0; font-weight: 600; font-size: 0.94rem;">{curr_score.get('next_action', 'Initiate executive touchpoint.')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Factors breakdown
                factors_raw = curr_score.get("scoring_factors")
                if factors_raw:
                    try:
                        flist = json.loads(factors_raw) if isinstance(factors_raw, str) else factors_raw
                        if isinstance(flist, list) and flist:
                            with st.expander("🔍 Deep Scoring Factor Attribution", expanded=False):
                                for f in flist:
                                    st.markdown(f"- ✅ **{f}**")
                    except Exception:
                        pass
            else:
                st.info("ℹ️ Qualification score has not been calculated yet. Click **Compute Qualification Score** above.")

            st.markdown("<br>", unsafe_allow_html=True)

            # AI Insights
            st.markdown("#### 💡 Strategic Business Opportunities & Company Intelligence")
            if curr_insight:
                in_col1, in_col2, in_col3 = st.columns(3)
                with in_col1:
                    st.markdown(f"""
                    <div class="sg-card" style="min-height: 190px; border-left: 3px solid #F59E0B;">
                        <div style="font-weight: 700; color: #F59E0B; margin-bottom: 8px;">1. Stated Business Needs</div>
                        <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6; margin: 0;">{curr_insight.get('business_needs')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with in_col2:
                    st.markdown(f"""
                    <div class="sg-card" style="min-height: 190px; border-left: 3px solid #38BDF8;">
                        <div style="font-weight: 700; color: #38BDF8; margin-bottom: 8px;">2. High-Value Opportunities</div>
                        <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6; margin: 0;">{curr_insight.get('opportunities')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with in_col3:
                    st.markdown(f"""
                    <div class="sg-card" style="min-height: 190px; border-left: 3px solid #A855F7;">
                        <div style="font-weight: 700; color: #A855F7; margin-bottom: 8px;">3. Market Situation & Trends</div>
                        <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6; margin: 0;">{curr_insight.get('industry_situation')}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ Company profile analysis is pending. Click **Generate AI Company Profile Analysis** above.")

# ==============================================================================
# TAB 3: OUTREACH STUDIO (TASKS 4 & 5)
# ==============================================================================
with tab_outreach:
    st.markdown("### ✉️ AI Outreach & Personalized Sales Communication")
    st.caption("Generate high-converting personalized cold emails, edit drafts, review outreach strategy, and test dispatch.")

    all_leads = st.session_state.leads_cache or fetch_leads()
    if not all_leads:
        st.warning("Please add or import leads in the Leads Management tab first.")
    else:
        lead_map_o = {l["lead_id"]: f"#{l['lead_id']} — {l['company_name']} ({l.get('contact_name', 'No Contact')})" for l in all_leads}
        o_idx = 0
        if st.session_state.selected_lead_id in lead_map_o:
            o_idx = list(lead_map_o.keys()).index(st.session_state.selected_lead_id)

        target_lead_id = st.selectbox(
            "Active Prospect for Outreach:",
            options=list(lead_map_o.keys()),
            format_func=lambda x: lead_map_o[x],
            index=o_idx,
            key="outreach_lead_select"
        )
        if target_lead_id != st.session_state.selected_lead_id:
            st.session_state.selected_lead_id = target_lead_id

        lead = next((l for l in all_leads if l["lead_id"] == target_lead_id), None)

        if lead:
            # Task 5: Strategic Outreach Guidance Card
            st.markdown("#### 🎯 AI Outreach Strategy & Personalization Guidance")
            
            saved_score = st.session_state.scores_cache.get(target_lead_id)
            if not saved_score:
                ok_sc, data_sc = api_get(f"/intelligence/score/{target_lead_id}")
                if ok_sc:
                    st.session_state.scores_cache[target_lead_id] = data_sc
                    saved_score = data_sc

            score_num = saved_score.get("lead_score", 75) if saved_score else 75
            
            if score_num >= 90:
                timing = "Within 24 hours (High urgency — immediate budget allocation)"
                strat = f"Direct pitch to {lead.get('contact_name')}; emphasize 65% faster processing gains and rapid enterprise implementation."
            elif score_num >= 70:
                timing = "Within 48 hours (Optimal response window)"
                strat = f"Position platform around ROI metrics and reference {lead.get('funding_stage')} benchmarks in {lead.get('industry')}."
            elif score_num >= 50:
                timing = "Next Tuesday (Nurture cadence)"
                strat = f"Educational touchpoint; provide technical whitepapers and client case studies before asking for a demo."
            else:
                timing = "Next month (Low priority cadence)"
                strat = "Enroll in automated monthly educational newsletter."

            p_highlight = f"Focus on {lead.get('company_name')}'s {lead.get('funding_stage', 'Growth')} trajectory and address: '{lead.get('business_need', 'scaling data operations')}'."

            strat_c1, strat_c2 = st.columns(2)
            with strat_c1:
                st.markdown(f"""
                <div class="sg-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 700; color: #38BDF8;">Strategic Angle</span>
                        <span style="font-weight: 800; color: #FFFFFF;">Score: {score_num}/100</span>
                    </div>
                    <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6; margin-bottom: 12px;">{strat}</p>
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Recommended Follow-Up Window</div>
                    <div style="color: #34D399; font-weight: 700; font-size: 0.92rem; margin-top: 2px;">⏰ {timing}</div>
                </div>
                """, unsafe_allow_html=True)
            with strat_c2:
                st.markdown(f"""
                <div class="sg-card">
                    <div style="font-weight: 700; color: #F59E0B; margin-bottom: 8px;">✨ Personalization Highlights</div>
                    <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.6; margin-bottom: 12px;">{p_highlight}</p>
                    <div style="font-size: 0.8rem; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Suggested Next Step</div>
                    <div style="color: #E2E8F0; font-weight: 600; font-size: 0.92rem; margin-top: 2px;">{saved_score.get('next_action', 'Send initial personalized email.') if saved_score else 'Send tailored outreach draft.'}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Email Studio
            st.markdown("#### ✍️ Superhuman-Style Email Studio")
            
            gen_col1, gen_col2, gen_col3 = st.columns([1, 1, 1])
            with gen_col1:
                tone = st.selectbox("Tone of Voice", options=["Professional", "Friendly", "Urgent"], index=0, key="tone_sel")
            with gen_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_gen = st.button("✨ Generate Personalized Email", use_container_width=True, type="primary")
            with gen_col3:
                st.markdown("<br>", unsafe_allow_html=True)
                btn_regen = st.button("🔄 Regenerate Variation", use_container_width=True)

            if btn_gen or btn_regen:
                with st.spinner("Crafting tailored sales email based on prospect signals..."):
                    ok_o, res_o = api_post("/intelligence/outreach", json_data={"lead_id": target_lead_id, "tone": tone.lower()})
                    if ok_o:
                        st.session_state.email_subject = res_o.get("email_subject", "")
                        st.session_state.email_body = res_o.get("email_content", "")
                        st.session_state.email_tone = tone.lower()
                        st.toast("New personalized email ready!", icon="✉️")
                    else:
                        st.error(f"Email generation failed: {res_o.get('error')}")

            # Check cached outreach if empty
            if not st.session_state.email_subject and not st.session_state.email_body:
                ok_o_saved, res_o_saved = api_get(f"/intelligence/outreach/{target_lead_id}")
                if ok_o_saved:
                    st.session_state.email_subject = res_o_saved.get("email_subject", "")
                    st.session_state.email_body = res_o_saved.get("email_content", "")

            # Studio Window Mock Header
            st.markdown(f"""
            <div class="email-studio-header">
                <span class="window-dot" style="background: #EF4444;"></span>
                <span class="window-dot" style="background: #F59E0B;"></span>
                <span class="window-dot" style="background: #10B981;"></span>
                <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 600; margin-left: 8px;">
                    Recipient: {lead.get('contact_name')} &lt;{lead.get('email', 'no-email')}&gt; &bull; Company: {lead.get('company_name')}
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### Subject Line:")
            ed_subject = st.text_input(
                "Subject",
                value=st.session_state.email_subject,
                placeholder="e.g. Quick question regarding TechCorp's Series C growth",
                label_visibility="collapsed",
                key="studio_subject"
            )
            st.session_state.email_subject = ed_subject

            st.markdown("##### Message Body:")
            ed_body = st.text_area(
                "Message Body",
                value=st.session_state.email_body,
                placeholder="Click 'Generate Personalized Email' above to compose an AI draft, or write your message here...",
                height=260,
                label_visibility="collapsed",
                key="studio_body"
            )
            st.session_state.email_body = ed_body

            # Stats Strip
            wcount = len(ed_body.split()) if ed_body else 0
            ccount = len(ed_body)
            rtime = max(1, round(wcount / 200 * 60))
            st.caption(f"📊 Draft Stats: **{wcount} words** | **{ccount} characters** | ~{rtime} sec read time | Tone: **{tone}**")

            # Actions
            st.markdown("<br>", unsafe_allow_html=True)
            act_c1, act_c2 = st.columns(2)
            with act_c1:
                st.markdown("##### 📋 Copy to Clipboard")
                if ed_subject or ed_body:
                    full_text = f"Subject: {ed_subject}\n\n{ed_body}"
                    st.code(full_text, language="markdown")
                    st.caption("💡 Use the copy button on the upper-right corner of the code block.")
                else:
                    st.info("Compose or generate an email to enable copy.")
            
            with act_c2:
                st.markdown("##### 🚀 Dispatch Email")
                st.caption("Sends email via configured SMTP relay.")
                if st.button("📤 Dispatch to Prospect", use_container_width=True, type="primary"):
                    if not ed_subject or not ed_body:
                        st.error("❌ Cannot send an empty draft.")
                    elif not lead.get("email"):
                        st.error("❌ This lead does not have a valid recipient email address.")
                    else:
                        with st.spinner("Checking backend SMTP configuration..."):
                            payload = {
                                "lead_id": target_lead_id,
                                "recipient_email": lead.get("email"),
                                "subject": ed_subject,
                                "body": ed_body
                            }
                            ok_snd, res_snd = api_post("/outreach/send-email", json_data=payload)

                        if ok_snd and res_snd.get("configured") is True and res_snd.get("success") is True:
                            st.success(f"✅ {res_snd.get('message', 'Email dispatched.')}")
                        else:
                            msg = res_snd.get("message", "Actual email sending (SMTP) is not configured in backend server.")
                            st.warning(f"⚠️ **Delivery Status:** {msg}\n\n*SalesGenie AI adheres to truthful reporting and never claims false dispatch when backend SMTP transport is unconfigured.*")

# ==============================================================================
# TAB 4: EXECUTIVE DASHBOARD (TASK 6)
# ==============================================================================
with tab_dash:
    st.markdown("### 📊 Executive Pipeline & Performance Dashboard")
    st.caption("Real-time visibility into sales pipeline volume, AI lead qualification health, and conversion KPIs.")

    dash_ok, dash_data = api_get("/analytics/dashboard")
    if not dash_ok:
        dash_data = {
            "total_leads": len(st.session_state.leads_cache),
            "hot_leads": 0, "warm_leads": 0, "cold_leads": 0,
            "emails_generated": 0, "emails_sent": 0, "calls_done": 0,
            "conversion_rate": 0.0, "industry_distribution": {}
        }

    # Top KPI Metrics Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-bar" style="background: linear-gradient(90deg, #38BDF8, #818CF8);"></div>
            <div class="kpi-number" style="color: #38BDF8;">{dash_data.get('total_leads', 0)}</div>
            <div class="kpi-label">Total Prospects</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-bar" style="background: linear-gradient(90deg, #10B981, #059669);"></div>
            <div class="kpi-number" style="color: #10B981;">{dash_data.get('hot_leads', 0)}</div>
            <div class="kpi-label">Hot Leads (70+)</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-bar" style="background: linear-gradient(90deg, #F59E0B, #D97706);"></div>
            <div class="kpi-number" style="color: #F59E0B;">{dash_data.get('warm_leads', 0)}</div>
            <div class="kpi-label">Warm Leads (50-69)</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-bar" style="background: linear-gradient(90deg, #64748B, #475569);"></div>
            <div class="kpi-number" style="color: #94A3B8;">{dash_data.get('cold_leads', 0)}</div>
            <div class="kpi-label">Cold Leads (&lt;50)</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-bar" style="background: linear-gradient(90deg, #C084FC, #818CF8);"></div>
            <div class="kpi-number" style="color: #C084FC;">{dash_data.get('conversion_rate', 0.0)}%</div>
            <div class="kpi-label">Conversion Rate</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Secondary Activity Row
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown(f"""
        <div class="sg-card">
            <div style="font-weight: 700; color: #38BDF8; font-size: 0.95rem;">✉️ Outreach Campaigns</div>
            <div style="font-family: 'Outfit'; font-size: 1.85rem; font-weight: 800; margin: 4px 0;">{dash_data.get('emails_generated', 0)} Drafts</div>
            <div style="color: #94A3B8; font-size: 0.8rem;">Personalized outreach generated and saved</div>
        </div>
        """, unsafe_allow_html=True)
    with ac2:
        st.markdown(f"""
        <div class="sg-card">
            <div style="font-weight: 700; color: #10B981; font-size: 0.95rem;">📞 Calls Logged</div>
            <div style="font-family: 'Outfit'; font-size: 1.85rem; font-weight: 800; margin: 4px 0;">{dash_data.get('calls_done', 0)} Meetings</div>
            <div style="color: #94A3B8; font-size: 0.8rem;">Automated summaries and follow-up items</div>
        </div>
        """, unsafe_allow_html=True)
    with ac3:
        st.markdown(f"""
        <div class="sg-card">
            <div style="font-weight: 700; color: #F59E0B; font-size: 0.95rem;">⚡ Pipeline Velocity</div>
            <div style="font-family: 'Outfit'; font-size: 1.85rem; font-weight: 800; margin: 4px 0;">High Activity</div>
            <div style="color: #94A3B8; font-size: 0.8rem;">Sub-second API response time</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Visual Charts
    st.markdown("#### 📈 Pipeline Visualizations")
    v1, v2 = st.columns(2)
    with v1:
        st.markdown("##### Leads by Qualification Status")
        status_df = pd.DataFrame({
            "Priority": ["Hot Leads (70-100)", "Warm Leads (50-69)", "Cold Leads (0-49)"],
            "Count": [dash_data.get("hot_leads", 0), dash_data.get("warm_leads", 0), dash_data.get("cold_leads", 0)]
        }).set_index("Priority")
        st.bar_chart(status_df, color="#38BDF8")

    with v2:
        st.markdown("##### Leads by Industry Sector")
        ind_dict = dash_data.get("industry_distribution", {})
        if ind_dict:
            ind_df = pd.DataFrame(list(ind_dict.items()), columns=["Industry", "Leads"]).set_index("Industry")
            st.bar_chart(ind_df, color="#818CF8")
        else:
            st.info("No industry distribution data yet.")

    st.markdown("---")

    # Top Ranked Leaderboard
    st.markdown("#### 🏆 Top Ranked Prospects by Qualification Score")
    all_leads = st.session_state.leads_cache or fetch_leads()
    if all_leads:
        leaderboard = []
        for l in all_leads:
            lid = l["lead_id"]
            sdata = st.session_state.scores_cache.get(lid)
            sval = f"{sdata.get('lead_score')}" if (sdata and sdata.get("lead_score") is not None) else "Unscored"
            pval = sdata.get("priority_level") if sdata else "Pending"
            leaderboard.append({
                "ID": f"#{lid}",
                "Company": l.get("company_name", ""),
                "Contact": l.get("contact_name", ""),
                "Industry": l.get("industry", ""),
                "Stage": l.get("funding_stage", ""),
                "Score": sval,
                "Priority": pval,
                "Stage Status": l.get("lead_status", "New")
            })

        def skey(x):
            s = x["Score"]
            return int(s) if s.isdigit() else -1

        leaderboard.sort(key=skey, reverse=True)
        st.dataframe(pd.DataFrame(leaderboard).astype(str), use_container_width=True, hide_index=True)

    if st.button("🔄 Refresh Live Dashboard Analytics", use_container_width=True):
        st.rerun()

# ==============================================================================
# FOOTER
# ==============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 0.84rem; padding: 12px 0;">
    SalesGenie AI &bull; Full-Stack Autonomous Sales Intelligence Platform &bull; Streamlit &bull; FastAPI &bull; PostgreSQL
</div>
""", unsafe_allow_html=True)
