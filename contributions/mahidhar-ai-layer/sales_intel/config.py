"""Central configuration for the AI/ML layer.

All tunable knobs live here (or in data/artifacts/*.json written by the Day-14
tuner) so that no magic numbers are buried in business logic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ARTIFACT_DIR = Path(os.getenv("SI_ARTIFACT_DIR", "data/artifacts"))
WEIGHTS_FILE = ARTIFACT_DIR / "scoring_weights.json"

# ---------------------------------------------------------------------------
# Feature normalisation caps: the raw count at which a feature is considered
# "fully saturated" (sub-score = 100). Values above the cap are clamped.
# ---------------------------------------------------------------------------
FEATURE_CAPS: dict[str, float] = {
    # engagement
    "email_opens": 16,
    "email_clicks": 6,
    "email_replies": 4,
    "inbound_replies": 4,
    "meetings_held": 3,
    "call_connect_rate": 0.75,         # 0..1
    "avg_response_latency_hours": 70,  # inverted: lower is better
    # fit
    "industry_match": 1.0,             # 0..1
    "company_size_score": 1.0,         # 0..1
    "seniority_score": 1.0,            # 0..1
    "tech_stack_overlap": 0.8,         # 0..1
    "budget_potential_usd": 120_000,
    # intent
    "pricing_page_visits": 8,
    "demo_requests": 3,
    "content_downloads": 5,
    "hiring_signal": 3,
    "competitor_mention": 2,
    # decision readiness
    "budget_confirmed": 1,
    "timeline_months": 15,             # inverted: shorter is readier
    "stakeholders_identified": 5,
    "procurement_stage": 3,            # 0..3
    "champion_identified": 1,
}

# Features where a LOWER raw value means a HIGHER sub-score.
INVERTED_FEATURES: set[str] = {"avg_response_latency_hours", "timeline_months"}

# ---------------------------------------------------------------------------
# Scoring model defaults (overridden by the Day-14 tuner output).
# ---------------------------------------------------------------------------
DEFAULT_SCORING: dict[str, Any] = {
    "weights": {
        "engagement": 0.30,
        "fit": 0.25,
        "intent": 0.25,
        "decision_readiness": 0.20,
    },
    "logistic_a": 0.11,   # steepness of the score -> probability curve
    "logistic_b": 55.0,   # score at which probability == 0.5
    "band_thresholds": {"hot": 75.0, "warm": 50.0},
    "min_accuracy_target": 0.85,
    "model_version": "m2-scoring-v0",
}

# ---------------------------------------------------------------------------
# Next-Best-Action rules (Day 15).
# ---------------------------------------------------------------------------
NBA_CONFIG: dict[str, Any] = {
    "cadence_offsets_days": [0, 3, 7, 14, 21],
    "max_touches_per_14_days": {
        "P0": 5,
        "P1": 4,
        "P2": 2,
        "P3": 1,
    },
    "quiet_hours": {"start": 20, "end": 8},
    "no_contact_weekdays": [6],          # Sunday, 0=Monday
    "channel_preference_by_seniority": {
        "c_level": ["linkedin", "email", "call"],
        "vp": ["email", "linkedin", "call"],
        "director": ["email", "call", "linkedin"],
        "manager": ["email", "call", "whatsapp"],
    },
    "stale_after_days": 14,
    "meeting_ask_after_score": 70.0,
}

# ---------------------------------------------------------------------------
# Summarisation settings (Day 24).
# ---------------------------------------------------------------------------
SUMMARY_CONFIG: dict[str, Any] = {
    "model": "gpt-4o-mini",
    "temperature": 0.1,
    "max_bullets": 6,
    "max_action_items": 10,
    "min_confidence": 0.35,
    "default_action_due_days": 3,
}
