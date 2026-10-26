"""Conversation intelligence endpoints (Module 5, local half).

CRM synchronisation lives in ``backend.routers.analytics`` (it shares the
analytics/operations surface); this router owns transcripts, summaries and the
stored sales interactions.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import SalesInteraction, get_db
from backend.deps import Principal, get_current_user, require_writer
from backend.errors import ApiError
from backend.intelligence import IntelligenceError, get_engine
from backend.routers._helpers import get_lead_or_404
from backend.schemas import ConversationRead, ConversationRequest

router = APIRouter(tags=["conversations"])


@router.post("/api/v1/conversations/summarize")
def summarize_conversation(
    body: ConversationRequest,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    get_lead_or_404(db, body.lead_id)
    try:
        engine = get_engine()
        summary, execution = engine.summarize_conversation(body.transcript, body.notes)
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Conversation summarisation failed: {exc}") from exc

    interaction = SalesInteraction(
        lead_id=body.lead_id,
        interaction_type=body.interaction_type,
        transcript=(body.transcript or body.notes)[:60000],
        summary=summary.executive_summary,
        key_points=list(summary.key_discussion_points),
        action_items=[item.model_dump() for item in summary.action_items],
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return {
        "id": interaction.id,
        "lead_id": interaction.lead_id,
        "created_at": interaction.created_at.isoformat(),
        "execution": execution.model_dump(),
        **summary.model_dump(),
    }


@router.post(
    "/api/v1/leads/{lead_id}/conversations",
    response_model=ConversationRead,
    status_code=201,
)
def save_conversation(
    lead_id: int,
    body: dict[str, Any],
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> ConversationRead:
    """Persist a summary produced elsewhere (for example by the AI package)."""
    get_lead_or_404(db, lead_id)
    summary = body.get("summary") if isinstance(body.get("summary"), dict) else {}
    if not isinstance(summary, dict):
        raise ApiError(422, "invalid_summary", "summary must be an object.")

    text = str(summary.get("executive_summary") or body.get("summary") or "").strip()
    if not text:
        raise ApiError(422, "empty_summary", "A non-empty summary is required.")

    interaction = SalesInteraction(
        lead_id=lead_id,
        interaction_type=str(body.get("interaction_type", "call"))[:60],
        transcript=str(body.get("transcript", ""))[:60000],
        summary=text[:20000],
        key_points=list(summary.get("key_discussion_points") or [])[:50],
        action_items=list(summary.get("action_items") or [])[:50],
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return ConversationRead.model_validate(interaction)


@router.get("/api/v1/leads/{lead_id}/conversations", response_model=list[ConversationRead])
def list_conversations(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationRead]:
    get_lead_or_404(db, lead_id)
    rows = db.scalars(
        select(SalesInteraction)
        .where(SalesInteraction.lead_id == lead_id)
        .order_by(SalesInteraction.interaction_date.desc(), SalesInteraction.id.desc())
    ).all()
    return [ConversationRead.model_validate(row) for row in rows]


@router.get("/api/v1/conversations/{interaction_id}", response_model=ConversationRead)
def get_conversation(
    interaction_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationRead:
    row = db.get(SalesInteraction, interaction_id)
    if row is None:
        raise ApiError(404, "interaction_not_found", f"Interaction {interaction_id} was not found.")
    return ConversationRead.model_validate(row)
