"""AI outreach generation and campaign persistence (Module 3).

Generation and sending are deliberately separate:

* ``POST /outreach/generate`` produces and stores a **draft**.
* ``POST /outreach/send`` returns ``501`` because no email delivery provider is
  configured (SRS D-05).  It never sends anything.
* ``POST /outreach/campaigns/{id}/mark-sent`` records that the user sent the
  message through an external tool; it does not transmit e-mail.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import OutreachCampaign, get_db
from backend.deps import Principal, get_current_user, require_writer
from backend.errors import ApiError
from backend.intelligence import IntelligenceError, get_engine
from backend.routers._helpers import get_lead_or_404
from backend.schemas import OutreachCampaignRead, OutreachDraftWrite, OutreachRequest
from backend.services.leads import lead_to_dict

router = APIRouter(tags=["outreach"])


@router.post("/api/v1/outreach/generate")
def generate_outreach(
    body: OutreachRequest,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    lead = get_lead_or_404(db, body.lead_id)
    try:
        engine = get_engine()
    except IntelligenceError as exc:
        raise ApiError(503, "ai_unavailable", str(exc)) from exc

    request = body.model_dump(exclude={"lead_id"})
    try:
        draft, execution = engine.generate_outreach(lead_to_dict(lead), request)
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Outreach generation failed: {exc}") from exc

    campaign = OutreachCampaign(
        lead_id=lead.id,
        subject=draft.subject_line or "",
        body=draft.body,
        channel=draft.channel,
        tone=body.tone,
        length=body.length,
        outreach_type=body.outreach_type,
        goal=body.goal,
        industry_context=body.industry or lead.industry,
        pain_points_used=list(body.pain_points),
        status="draft",
        provider=execution.provider,
        model=execution.model,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "lead_id": campaign.lead_id,
        "status": campaign.status,
        "execution": execution.model_dump(),
        **draft.model_dump(),
    }


@router.post("/api/v1/leads/{lead_id}/outreach-drafts", response_model=OutreachCampaignRead, status_code=201)
def save_outreach_draft(
    lead_id: int,
    body: OutreachDraftWrite,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> OutreachCampaignRead:
    get_lead_or_404(db, lead_id)
    campaign = OutreachCampaign(
        lead_id=lead_id,
        subject=body.subject,
        body=body.body,
        tone=body.tone,
        status=body.status,
        provider="user-supplied",
        model="edited",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return OutreachCampaignRead.model_validate(campaign)


@router.get("/api/v1/leads/{lead_id}/outreach-drafts", response_model=list[OutreachCampaignRead])
def list_outreach_drafts(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OutreachCampaignRead]:
    get_lead_or_404(db, lead_id)
    rows = db.scalars(
        select(OutreachCampaign)
        .where(OutreachCampaign.lead_id == lead_id)
        .order_by(OutreachCampaign.created_at.desc(), OutreachCampaign.id.desc())
    ).all()
    return [OutreachCampaignRead.model_validate(row) for row in rows]


@router.get("/api/v1/outreach/campaigns/{campaign_id}", response_model=OutreachCampaignRead)
def get_campaign(
    campaign_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachCampaignRead:
    campaign = db.get(OutreachCampaign, campaign_id)
    if campaign is None:
        raise ApiError(404, "campaign_not_found", f"Outreach draft {campaign_id} was not found.")
    return OutreachCampaignRead.model_validate(campaign)


@router.patch("/api/v1/outreach/campaigns/{campaign_id}", response_model=OutreachCampaignRead)
def edit_campaign(
    campaign_id: int,
    body: OutreachDraftWrite,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> OutreachCampaignRead:
    campaign = db.get(OutreachCampaign, campaign_id)
    if campaign is None:
        raise ApiError(404, "campaign_not_found", f"Outreach draft {campaign_id} was not found.")
    campaign.subject = body.subject
    campaign.body = body.body
    campaign.tone = body.tone
    campaign.status = body.status
    campaign.provider = "user-supplied"
    db.commit()
    db.refresh(campaign)
    return OutreachCampaignRead.model_validate(campaign)


@router.post("/api/v1/outreach/campaigns/{campaign_id}/mark-sent", response_model=OutreachCampaignRead)
def mark_sent(
    campaign_id: int,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> OutreachCampaignRead:
    campaign = db.get(OutreachCampaign, campaign_id)
    if campaign is None:
        raise ApiError(404, "campaign_not_found", f"Outreach draft {campaign_id} was not found.")
    campaign.status = "sent"
    db.commit()
    db.refresh(campaign)
    return OutreachCampaignRead.model_validate(campaign)


@router.post("/api/v1/outreach/send")
def send_outreach(_: Principal = Depends(require_writer)) -> dict[str, Any]:
    raise ApiError(
        501,
        "email_transport_not_configured",
        "No e-mail delivery provider is configured. Outreach content can be generated, "
        "edited and exported, but this build never sends e-mail. See SRS decision D-05.",
    )


@router.get("/api/v1/outreach/{lead_id}", response_model=list[OutreachCampaignRead], include_in_schema=False)
def list_outreach_alias(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OutreachCampaignRead]:
    """Backwards-compatible alias for the original draft endpoint."""
    return list_outreach_drafts(lead_id=lead_id, _=_, db=db)
