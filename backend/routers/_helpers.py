"""Shared router helpers."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db import Lead
from backend.errors import ApiError


def get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise ApiError(404, "lead_not_found", f"Lead {lead_id} was not found.")
    return lead
