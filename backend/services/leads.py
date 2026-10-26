"""Lead domain services: serialisation, duplicate detection and updates."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import Lead
from backend.schemas import LeadRead, derived_status

#: Columns that a client may update.  ``email_key`` is derived, never assigned
#: directly, which prevents mass-assignment of the duplicate-detection key.
UPDATABLE_FIELDS: tuple[str, ...] = (
    "company_name",
    "industry",
    "contact_name",
    "email",
    "phone",
    "website",
    "company_size",
    "annual_revenue",
    "funding_stage",
    "tech_stack",
    "company_description",
    "prospect_role",
    "engagement_history",
    "explicit_needs",
    "response_behavior",
    "user_research",
    "pain_points",
    "lead_source",
)


def normalise_email(email: str | None) -> str:
    return (email or "").strip().lower()


def email_key_for(email: str | None) -> str | None:
    value = normalise_email(email)
    return value or None


def lead_to_read(lead: Lead) -> LeadRead:
    return LeadRead(
        id=str(lead.id),
        company_name=lead.company_name,
        industry=lead.industry,
        contact_name=lead.contact_name,
        email=lead.email,
        phone=lead.phone,
        website=lead.website,
        company_size=lead.company_size,
        annual_revenue=lead.annual_revenue,
        funding_stage=lead.funding_stage,
        tech_stack=lead.tech_stack,
        company_description=lead.company_description,
        prospect_role=lead.prospect_role,
        engagement_history=lead.engagement_history,
        explicit_needs=lead.explicit_needs,
        response_behavior=lead.response_behavior,
        user_research=lead.user_research,
        pain_points=lead.pain_points,
        lead_source=lead.lead_source,
        stage=lead.lifecycle_stage,
        status=derived_status(lead.lifecycle_stage),
        owner_id=lead.owner_id,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def lead_to_dict(lead: Lead) -> dict[str, Any]:
    """Shape consumed by the intelligence layer (matches the frontend contract)."""
    return lead_to_read(lead).model_dump(mode="json")


def find_duplicate(
    db: Session,
    *,
    email: str | None,
    company_name: str | None,
    contact_name: str | None,
    exclude_id: int | None = None,
) -> tuple[Lead | None, str | None]:
    """Return ``(lead, reason)`` for an existing duplicate, else ``(None, None)``.

    Documented policy:

    1. A non-empty e-mail is the authoritative key (case-insensitive).
    2. Without an e-mail, a lead with the same company **and** contact name is a
       duplicate (case-insensitive, whitespace-normalised).
    """
    key = email_key_for(email)
    if key:
        stmt = select(Lead).where(Lead.email_key == key)
        if exclude_id is not None:
            stmt = stmt.where(Lead.id != exclude_id)
        match = db.scalar(stmt)
        if match is not None:
            return match, "email"

    company = " ".join((company_name or "").split()).lower()
    contact = " ".join((contact_name or "").split()).lower()
    if company and contact:
        stmt = select(Lead).where(
            func.lower(func.trim(Lead.company_name)) == company,
            func.lower(func.trim(Lead.contact_name)) == contact,
        )
        if exclude_id is not None:
            stmt = stmt.where(Lead.id != exclude_id)
        match = db.scalar(stmt)
        if match is not None:
            return match, "company+contact"

    return None, None


def apply_update(lead: Lead, values: dict[str, Any]) -> None:
    """Apply a validated partial update, keeping derived columns consistent."""
    stage = values.pop("stage", None)
    values.pop("status", None)
    for field in UPDATABLE_FIELDS:
        if field in values and values[field] is not None:
            setattr(lead, field, values[field])
    if "email" in values:
        lead.email = normalise_email(lead.email)
        lead.email_key = email_key_for(lead.email)
    if stage is not None:
        lead.lifecycle_stage = stage
