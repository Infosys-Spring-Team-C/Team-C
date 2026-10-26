"""Company analysis / lead intelligence endpoints (Module 2)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import CompanyInsight, get_db
from backend.deps import Principal, get_current_user, require_writer
from backend.errors import ApiError
from backend.intelligence import IntelligenceError, get_engine
from backend.routers._helpers import get_lead_or_404
from backend.schemas import IntelligenceRequest
from backend.services.leads import lead_to_dict

router = APIRouter(tags=["intelligence"])


def _engine():
    try:
        return get_engine()
    except IntelligenceError as exc:
        raise ApiError(503, "ai_unavailable", str(exc)) from exc


def _persist(db: Session, lead_id: int, intelligence, execution) -> CompanyInsight:
    record = CompanyInsight(
        lead_id=lead_id,
        business_needs=[item.model_dump() for item in intelligence.possible_needs],
        opportunities=[item.model_dump() for item in intelligence.opportunities],
        pain_points=[item.model_dump() for item in intelligence.potential_challenges],
        industry_context=intelligence.company_overview,
        qualification=intelligence.qualification.model_dump(),
        recommended_value_proposition=intelligence.product_industry_fit,
        discovery_questions=list(intelligence.discovery_questions),
        missing_information=list(intelligence.missing_information),
        supporting_evidence=[item.model_dump() for item in intelligence.supported_facts],
        provider=execution.provider,
        model=execution.model,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/api/v1/leads/{lead_id}/insights")
@router.post("/api/v1/intelligence/analyze/{lead_id}", include_in_schema=False)
def analyze_lead(
    lead_id: int,
    body: IntelligenceRequest | None = None,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    lead = get_lead_or_404(db, lead_id)
    payload = lead_to_dict(lead)
    if body and body.product_service:
        payload["product_service"] = body.product_service
    if body and body.extra_context:
        payload["user_research"] = (
            (payload.get("user_research") or "") + "\n" + body.extra_context
        ).strip()

    engine = _engine()
    try:
        intelligence, execution = engine.analyze_lead(payload)
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Company analysis failed: {exc}") from exc

    record = _persist(db, lead_id, intelligence, execution)
    return {
        "id": record.id,
        "lead_id": lead_id,
        "created_at": record.created_at.isoformat(),
        "execution": execution.model_dump(),
        **intelligence.model_dump(),
    }


@router.get("/api/v1/leads/{lead_id}/insights")
@router.get("/api/v1/intelligence/{lead_id}", include_in_schema=False)
def list_insights(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_lead_or_404(db, lead_id)
    rows = db.scalars(
        select(CompanyInsight)
        .where(CompanyInsight.lead_id == lead_id)
        .order_by(CompanyInsight.created_at.desc(), CompanyInsight.id.desc())
    ).all()
    return [
        {
            "id": row.id,
            "lead_id": row.lead_id,
            "business_needs": row.business_needs,
            "opportunities": row.opportunities,
            "pain_points": row.pain_points,
            "industry_context": row.industry_context,
            "qualification": row.qualification,
            "recommended_value_proposition": row.recommended_value_proposition,
            "discovery_questions": row.discovery_questions,
            "missing_information": row.missing_information,
            "supporting_evidence": row.supporting_evidence,
            "provider": row.provider,
            "model": row.model,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
