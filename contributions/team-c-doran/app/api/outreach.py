"""Generation and history endpoints for lead outreach campaigns."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.outreach import OutreachRequest, OutreachResponse
from app.services import ai_service
from database.models import Lead, OutreachCampaign

router = APIRouter(prefix="/intelligence/outreach", tags=["outreach"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=OutreachResponse, status_code=status.HTTP_201_CREATED)
async def generate_outreach(
    payload: OutreachRequest,
    db: DatabaseSession,
) -> OutreachCampaign:
    """Generate, persist, and return an outreach campaign for a lead."""
    lead = db.get(Lead, payload.lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    lead_data = {
        "lead_id": lead.lead_id,
        "company_name": lead.company_name,
        "industry": lead.industry,
        "contact_name": lead.contact_name,
        "lead_status": lead.lead_status,
        "tech_stack": lead.tech_stack,
        "funding_stage": lead.funding_stage,
        "focus_points": payload.focus_points,
    }
    try:
        generated = await ai_service.invoke_with_timeout(
            ai_service.generate_outreach_email, lead_data, payload.tone
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Outreach generation timed out.",
        ) from exc
    campaign = OutreachCampaign(
        lead_id=lead.lead_id,
        tone=payload.tone,
        email_subject=generated["email_subject"],
        email_content=generated["email_content"],
        follow_up_strategy=generated["follow_up_strategy"],
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{lead_id}", response_model=list[OutreachResponse])
def get_outreach_history(lead_id: int, db: DatabaseSession) -> list[OutreachCampaign]:
    """Return campaign history for a lead, newest campaign first."""
    if db.get(Lead, lead_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    statement = (
        select(OutreachCampaign)
        .where(OutreachCampaign.lead_id == lead_id)
        .order_by(OutreachCampaign.created_at.desc(), OutreachCampaign.campaign_id.desc())
    )
    return list(db.scalars(statement).all())
