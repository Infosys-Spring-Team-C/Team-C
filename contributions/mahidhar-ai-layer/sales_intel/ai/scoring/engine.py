"""Feature engineering + the lead scoring engine (Module 4).

Scoring is deliberately transparent: four interpretable dimensions each mapped to
a 0-100 sub-score, combined with a weight vector that the Day-14 tuner learns,
then mapped to a conversion probability with a calibrated logistic curve.
Everything is deterministic so scores are reproducible and auditable in the
Milestone-2 review.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from sales_intel.config import DEFAULT_SCORING, FEATURE_CAPS, INVERTED_FEATURES, WEIGHTS_FILE
from sales_intel.schemas import LeadFeatures, LeadScore
from sales_intel.utils import utcnow

DIMENSIONS: tuple[str, ...] = ("engagement", "fit", "intent", "decision_readiness")

# Which raw features feed which dimension.
DIMENSION_FEATURES: dict[str, tuple[str, ...]] = {
    "engagement": (
        "email_opens",
        "email_clicks",
        "email_replies",
        "inbound_replies",
        "meetings_held",
        "call_connect_rate",
        "avg_response_latency_hours",
    ),
    "fit": (
        "industry_match",
        "company_size_score",
        "seniority_score",
        "tech_stack_overlap",
        "budget_potential_usd",
    ),
    "intent": (
        "pricing_page_visits",
        "demo_requests",
        "content_downloads",
        "hiring_signal",
        "competitor_mention",
    ),
    "decision_readiness": (
        "budget_confirmed",
        "timeline_months",
        "stakeholders_identified",
        "procurement_stage",
        "champion_identified",
    ),
}


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def load_scoring_config(path: Path | None = None) -> dict[str, Any]:
    """Load tuner output if present, else fall back to the defaults."""
    cfg = json.loads(json.dumps(DEFAULT_SCORING))  # deep copy
    f = path or WEIGHTS_FILE
    if Path(f).exists():
        with open(f, encoding="utf-8") as fh:
            tuned = json.load(fh)
        cfg["weights"] = tuned.get("weights", cfg["weights"])
        cfg["logistic_a"] = tuned.get("logistic_a", cfg["logistic_a"])
        cfg["logistic_b"] = tuned.get("logistic_b", cfg["logistic_b"])
        cfg["model_version"] = tuned.get("model_version", cfg["model_version"])
    _validate_weights(cfg["weights"])
    return cfg


def _validate_weights(w: dict[str, float]) -> None:
    missing = set(DIMENSIONS) - set(w)
    if missing:
        raise ValueError(f"weights missing dimensions: {sorted(missing)}")
    if any(v < 0 for v in w.values()):
        raise ValueError("weights must be non-negative")
    if not math.isclose(sum(w.values()), 1.0, abs_tol=1e-6):
        raise ValueError(f"weights must sum to 1.0, got {sum(w.values()):.6f}")


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def _normalise(feature: str, raw: float) -> float:
    cap = FEATURE_CAPS[feature]
    if cap <= 0:
        raise ValueError(f"cap for {feature} must be > 0")
    ratio = max(0.0, min(1.0, float(raw) / cap))
    if feature in INVERTED_FEATURES:
        ratio = 1.0 - ratio
    return round(ratio * 100.0, 2)


def dimension_subscores(lead: LeadFeatures) -> dict[str, float]:
    """Equal-weight mean of the normalised features inside each dimension."""
    out: dict[str, float] = {}
    for dim, feats in DIMENSION_FEATURES.items():
        vals = [_normalise(f, getattr(lead, f)) for f in feats]
        out[dim] = round(sum(vals) / len(vals), 2)
    return out


def composite_score(subscores: dict[str, float], weights: dict[str, float]) -> float:
    total = sum(subscores[d] * weights[d] for d in DIMENSIONS)
    return round(max(0.0, min(100.0, total)), 2)


def conversion_probability(score: float, a: float, b: float) -> float:
    """Logistic mapping score -> P(conversion); calibrated by the tuner."""
    return round(1.0 / (1.0 + math.exp(-a * (score - b))), 4)


def _band(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds["hot"]:
        return "Hot"
    if score >= thresholds["warm"]:
        return "Warm"
    return "Cold"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def score_lead(lead: LeadFeatures, config: dict[str, Any] | None = None) -> LeadScore:
    """Score one lead, returning a full explanation payload."""
    cfg = config or load_scoring_config()
    subs = dimension_subscores(lead)
    weights = cfg["weights"]
    total = composite_score(subs, weights)

    # Contribution drivers: how many of the 100 points each dimension supplied.
    drivers = sorted(
        (
            {
                "dimension": d,
                "subscore": subs[d],
                "weight": round(weights[d], 4),
                "contribution": round(subs[d] * weights[d], 2),
                "share_of_score_pct": round(
                    (subs[d] * weights[d] / total * 100) if total else 0.0, 1
                ),
            }
            for d in DIMENSIONS
        ),
        key=lambda x: x["contribution"],
        reverse=True,
    )

    return LeadScore(
        lead_id=lead.lead_id,
        score=total,
        band=_band(total, cfg["band_thresholds"]),  # type: ignore[arg-type]
        conversion_probability=conversion_probability(
            total, cfg["logistic_a"], cfg["logistic_b"]
        ),
        subscores=subs,
        drivers=drivers,
        model_version=cfg["model_version"],
        scored_at=utcnow(),
    )


def score_batch(leads: list[LeadFeatures], config: dict[str, Any] | None = None) -> list[LeadScore]:
    cfg = config or load_scoring_config()
    return [score_lead(l, cfg) for l in leads]
