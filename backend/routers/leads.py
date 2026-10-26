"""Prospect / lead management endpoints (Module 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import Lead, get_db
from backend.deps import Principal, get_current_user, require_manager, require_writer
from backend.errors import ApiError
from backend.routers._helpers import get_lead_or_404
from backend.schemas import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    ImportReport,
    LeadCreate,
    LeadRead,
    LeadUpdate,
    normalise_stage,
)
from backend.services.csv_import import ImportValidationError, import_leads
from backend.services.leads import (
    apply_update,
    email_key_for,
    find_duplicate,
    lead_to_read,
    normalise_email,
)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


def _duplicate_error(match: Lead, reason: str) -> ApiError:
    return ApiError(
        409,
        "duplicate_lead",
        "A lead with the same identity already exists.",
        meta={"matched_lead_id": str(match.id), "match_reason": reason},
    )


@router.post("", response_model=LeadRead, status_code=201)
@router.post("/", response_model=LeadRead, status_code=201, include_in_schema=False)
def create_lead(
    body: LeadCreate,
    principal: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> LeadRead:
    email = normalise_email(body.email)
    match, reason = find_duplicate(
        db, email=email, company_name=body.company_name, contact_name=body.contact_name
    )
    if match is not None:
        raise _duplicate_error(match, reason or "unknown")

    lead = Lead(
        company_name=body.company_name,
        industry=body.industry,
        contact_name=body.contact_name,
        email=email,
        email_key=email_key_for(email),
        phone=body.phone,
        website=body.website,
        company_size=body.company_size,
        annual_revenue=body.annual_revenue,
        funding_stage=body.funding_stage,
        tech_stack=body.tech_stack,
        company_description=body.company_description,
        prospect_role=body.prospect_role,
        engagement_history=body.engagement_history,
        explicit_needs=body.explicit_needs,
        response_behavior=body.response_behavior,
        user_research=body.user_research,
        pain_points=body.pain_points,
        lead_source=body.lead_source,
        lifecycle_stage=body.stage,
        owner_id=principal.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead_to_read(lead)


@router.get("", response_model=list[LeadRead])
@router.get("/", response_model=list[LeadRead], include_in_schema=False)
def list_leads(
    response: Response,
    query: str = Query(default="", max_length=200),
    stage: str = Query(default="", max_length=40),
    industry: str = Query(default="", max_length=160),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=500),
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LeadRead]:
    settings = get_settings()
    size = page_size or settings.default_page_size
    if size > settings.max_page_size:
        raise ApiError(
            422, "page_size_too_large", f"page_size may not exceed {settings.max_page_size}."
        )

    filters = []
    if query.strip():
        needle = f"%{query.strip().lower()}%"
        filters.append(
            func.lower(Lead.company_name).like(needle)
            | func.lower(Lead.contact_name).like(needle)
            | func.lower(Lead.email).like(needle)
            | func.lower(Lead.industry).like(needle)
        )
    if industry.strip():
        filters.append(func.lower(Lead.industry) == industry.strip().lower())
    if stage.strip():
        try:
            filters.append(Lead.lifecycle_stage == normalise_stage(stage))
        except ValueError as exc:
            raise ApiError(422, "invalid_stage", str(exc)) from exc

    base = select(Lead)
    if filters:
        base = base.where(*filters)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Lead.created_at.desc(), Lead.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(size)
    return [lead_to_read(row) for row in rows]


@router.post("/duplicate-check", response_model=DuplicateCheckResponse)
def duplicate_check(
    body: DuplicateCheckRequest,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DuplicateCheckResponse:
    match, reason = find_duplicate(
        db,
        email=body.email,
        company_name=body.company_name,
        contact_name=body.contact_name,
    )
    return DuplicateCheckResponse(
        is_duplicate=match is not None,
        matched_lead_id=str(match.id) if match else None,
        match_reason=reason,
    )


@router.post("/import", response_model=ImportReport)
async def import_csv(
    file: UploadFile = File(...),
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> ImportReport:
    settings = get_settings()
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise ApiError(415, "unsupported_file_type", "Only .csv files are accepted.")

    content = await file.read(settings.max_csv_bytes + 1)
    if len(content) > settings.max_csv_bytes:
        raise ApiError(
            413,
            "file_too_large",
            f"CSV exceeds the {settings.max_csv_bytes // 1_000_000} MB upload limit.",
        )
    if not content.strip():
        raise ApiError(422, "empty_file", "The uploaded CSV file is empty.")

    try:
        return import_leads(db, file.filename, content, settings)
    except ImportValidationError as exc:
        db.rollback()
        raise ApiError(422, "invalid_csv", str(exc)) from exc


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeadRead:
    return lead_to_read(get_lead_or_404(db, lead_id))


@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> LeadRead:
    lead = get_lead_or_404(db, lead_id)
    values = body.model_dump(exclude_unset=True)

    new_email = values.get("email")
    new_company = values.get("company_name", lead.company_name)
    new_contact = values.get("contact_name", lead.contact_name)
    if any(key in values for key in ("email", "company_name", "contact_name")):
        match, reason = find_duplicate(
            db,
            email=new_email if new_email is not None else lead.email,
            company_name=new_company,
            contact_name=new_contact,
            exclude_id=lead.id,
        )
        if match is not None:
            raise _duplicate_error(match, reason or "unknown")

    apply_update(lead, values)
    db.commit()
    db.refresh(lead)
    return lead_to_read(lead)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    _: Principal = Depends(require_manager),
    db: Session = Depends(get_db),
) -> Response:
    lead = get_lead_or_404(db, lead_id)
    db.delete(lead)
    db.commit()
    return Response(status_code=204)
