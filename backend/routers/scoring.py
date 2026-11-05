"""Lead scoring and conversion-probability endpoints (Module 4).

The default AI engine returns eight explainable factors from the reviewed AI
package; the adapter maps them onto the four SRS FR-030 dimensions and this
router aggregates them into the canonical `fit/intent/engagement/decision
readiness` columns.  The offline heuristic engine returns four factors that are
already dimensions.

``conversion_probability`` is only populated by a calibrated model.  Neither
engine ships one, so it stays ``null`` with an explicitly uncalibrated band; a
heuristic is never presented as a trained probability.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import LeadScore, get_db
from backend.deps import Principal, get_current_user, require_writer
from backend.errors import ApiError
from backend.intelligence import IntelligenceError, get_engine
from backend.routers._helpers import get_lead_or_404
from backend.services.leads import lead_to_dict

router = APIRouter(tags=["scoring"])

_DIMENSION_COLUMNS = {
    "Fit": "fit_score",
    "Intent": "intent_score",
    "Engagement": "engagement_score",
    "Decision readiness": "decision_readiness_score",
}

#: Heuristic factors already are the four SRS dimensions and carry no
#: ``dimension`` annotation.  The AI package returns eight finer-grained
#: factors that the adapter annotates with one of the four dimensions.
_NAME_TO_DIMENSION = {
    "Company fit": "Fit",
    "Company Fit": "Fit",
    "Intent": "Intent",
    "Engagement": "Engagement",
    "Decision readiness": "Decision readiness",
}


def dimension_scores(factors: list[Any]) -> dict[str, int]:
    """Aggregate arbitrary score factors into the four SRS FR-030 dimensions.

    Each dimension is reported as a 0-100 percentage of the weight it carries,
    so the eight-factor AI model and the four-factor offline engine populate the
    same database columns without inventing or discarding signal.
    """
    totals: dict[str, dict[str, float]] = {
        dimension: {"points": 0.0, "weight": 0.0} for dimension in _DIMENSION_COLUMNS
    }
    for factor in factors:
        dimension = getattr(factor, "dimension", None) or _NAME_TO_DIMENSION.get(
            getattr(factor, "name", "")
        )
        if dimension not in totals:
            continue
        totals[dimension]["points"] += float(getattr(factor, "points", 0.0) or 0.0)
        totals[dimension]["weight"] += float(getattr(factor, "weight", 0.0) or 0.0)

    return {
        column: (
            max(0, min(100, int(round(bucket["points"] / bucket["weight"] * 100))))
            if bucket["weight"]
            else 0
        )
        for dimension, column in _DIMENSION_COLUMNS.items()
        for bucket in (totals[dimension],)
    }


def _serialise(row: LeadScore) -> dict[str, Any]:
    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "score": row.score,
        "qualification_category": (
            "Qualified"
            if row.priority_level == "hot"
            else "Nurture"
            if row.priority_level == "warm"
            else "Low priority"
        ),
        "conversion_probability": row.conversion_probability,
        "priority_level": row.priority_level,
        "factors": row.factors,
        "positive_signals": [f["explanation"] for f in row.factors if f.get("signal") == "positive"],
        "negative_signals": [f["explanation"] for f in row.factors if f.get("signal") == "negative"],
        "missing_information": [f["explanation"] for f in row.factors if f.get("signal") == "missing"],
        "recommended_next_action": row.recommended_next_action,
        "explanation": row.explanation,
        "model_version": row.model_version,
        "created_at": row.created_at.isoformat(),
    }


@router.post("/api/v1/leads/{lead_id}/scores")
@router.post("/api/v1/scoring/{lead_id}", include_in_schema=False)
def score_lead(
    lead_id: int,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    lead = get_lead_or_404(db, lead_id)
    try:
        engine = get_engine()
        result, execution = engine.score_lead(lead_to_dict(lead))
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Lead scoring failed: {exc}") from exc

    factor_points = dimension_scores(result.factors)
    priority = "hot" if result.score >= 70 else "warm" if result.score >= 45 else "cold"

    row = LeadScore(
        lead_id=lead_id,
        score=result.score,
        conversion_probability=result.conversion_probability,
        priority_level=priority,
        fit_score=factor_points["fit_score"],
        intent_score=factor_points["intent_score"],
        engagement_score=factor_points["engagement_score"],
        decision_readiness_score=factor_points["decision_readiness_score"],
        factors=[factor.model_dump() for factor in result.factors],
        explanation=result.probability_note,
        recommended_next_action=result.recommended_next_action,
        model_version=f"{execution.engine}:{execution.model}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    payload = _serialise(row)
    payload["execution"] = execution.model_dump()
    payload["probability_band"] = result.probability_band
    payload["probability_note"] = result.probability_note
    payload["methodology_note"] = result.methodology_note
    return payload


@router.get("/api/v1/leads/{lead_id}/scores")
@router.get("/api/v1/scoring/{lead_id}", include_in_schema=False)
def list_scores(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_lead_or_404(db, lead_id)
    rows = db.scalars(
        select(LeadScore)
        .where(LeadScore.lead_id == lead_id)
        .order_by(LeadScore.created_at.desc(), LeadScore.id.desc())
    ).all()
    return [_serialise(row) for row in rows]


@router.get("/api/v1/leads/{lead_id}/scores/latest")
def latest_score(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_lead_or_404(db, lead_id)
    row = db.scalar(
        select(LeadScore)
        .where(LeadScore.lead_id == lead_id)
        .order_by(LeadScore.created_at.desc(), LeadScore.id.desc())
        .limit(1)
    )
    if row is None:
        raise ApiError(404, "score_not_found", "No score has been generated for this lead yet.")
    return _serialise(row)
