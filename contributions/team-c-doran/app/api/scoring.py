"""Lead scoring endpoints."""

import json
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.scoring import LeadScoreResponse, LeadScoreResult
from app.services import ai_service
from database.models import Lead, LeadScore

router = APIRouter(prefix="/intelligence/score", tags=["scoring"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _parse_scoring_result(raw_result: Any) -> LeadScoreResult:
    """Parse and validate a dictionary or JSON string from the scoring service."""
    try:
        if isinstance(raw_result, str):
            raw_result = json.loads(raw_result)
        return LeadScoreResult.model_validate(raw_result)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Scoring service returned an invalid response.",
        ) from exc


@router.post("/{lead_id}", response_model=LeadScoreResponse)
async def score_lead(lead_id: int, db: DatabaseSession) -> LeadScore:
    """Calculate and upsert the current score card for a lead."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    lead_dict = {
        "lead_id": lead.lead_id,
        "company_name": lead.company_name,
        "industry": lead.industry,
        "contact_name": lead.contact_name,
        "funding_stage": lead.funding_stage,
        "company_size": lead.company_size,
        "tech_stack": lead.tech_stack,
        "revenue": lead.revenue,
        "status": lead.lead_status,
    }
    try:
        raw_result = await ai_service.invoke_with_timeout(ai_service.score_lead, lead_dict)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Lead scoring timed out.",
        ) from exc
    result = _parse_scoring_result(raw_result)
    values = result.model_dump()

    score_card = db.scalar(select(LeadScore).where(LeadScore.lead_id == lead_id))
    if score_card is None:
        score_card = LeadScore(lead_id=lead_id, **values)
        db.add(score_card)
    else:
        for field, value in values.items():
            setattr(score_card, field, value)
        score_card.calculated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(score_card)
    return score_card


@router.get("/{lead_id}", response_model=LeadScoreResponse)
def get_lead_score(lead_id: int, db: DatabaseSession) -> LeadScore:
    """Return the current score card for a lead or 404 if it is not available."""
    score_card = db.scalar(select(LeadScore).where(LeadScore.lead_id == lead_id))
    if score_card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead score not found",
        )
    return score_card
