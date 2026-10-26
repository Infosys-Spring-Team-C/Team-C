"""Lead scoring and conversion-probability endpoints (Module 4).

The score is an explainable heuristic over the four factors required by SRS
FR-030.  ``conversion_probability`` is only populated when a calibrated model is
configured; the shipped engine returns ``null`` plus an explicitly uncalibrated
band, so a heuristic is never presented as a trained probability.
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

_FACTOR_COLUMNS = {
    "Company fit": "fit_score",
    "Intent": "intent_score",
    "Engagement": "engagement_score",
    "Decision readiness": "decision_readiness_score",
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

    factor_points = {
        _FACTOR_COLUMNS.get(factor.name, factor.name): int(round(factor.normalized_value * 100))
        for factor in result.factors
    }
    priority = "hot" if result.score >= 70 else "warm" if result.score >= 45 else "cold"

    row = LeadScore(
        lead_id=lead_id,
        score=result.score,
        conversion_probability=result.conversion_probability,
        priority_level=priority,
        fit_score=factor_points.get("fit_score", 0),
        intent_score=factor_points.get("intent_score", 0),
        engagement_score=factor_points.get("engagement_score", 0),
        decision_readiness_score=factor_points.get("decision_readiness_score", 0),
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
