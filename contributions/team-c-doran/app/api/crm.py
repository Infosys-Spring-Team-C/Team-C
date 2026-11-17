"""CRM synchronization and audit endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import AuthenticatedUser, require_role
from app.schemas.crm import CRMStatusResponse, CRMSyncAction, CRMSyncLogResponse, CRMSyncRequest
from app.services import crm_service
from database.models import CRMSyncLog, Lead

router = APIRouter(prefix="/crm", tags=["crm"])
DatabaseSession = Annotated[Session, Depends(get_db)]
RECENT_WINDOW_HOURS = 24


@router.post("/sync/{lead_id}", response_model=CRMSyncLogResponse, status_code=201)
def sync_lead_to_crm(
    lead_id: int,
    request: CRMSyncRequest,
    db: DatabaseSession,
    _authorized_user: Annotated[
        AuthenticatedUser, Depends(require_role(["admin", "manager"]))
    ],
) -> CRMSyncLog:
    """Map a lead to the standard CRM payload, simulate sync, and log the attempt."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    action = cast(CRMSyncAction, request.action)
    payload = crm_service.build_standardized_payload(lead, action)
    sync_type = crm_service.ACTION_TO_SYNC_TYPE[action]
    try:
        result = crm_service.simulate_crm_sync(request.crm_provider, payload)
        sync_status = "success" if result.get("status") == "success" else "failed"
        error_message = result.get("error_message")
    except Exception as exc:  # Record adapter failures in the audit log.
        sync_status = "failed"
        error_message = str(exc) or "CRM synchronization failed."

    sync_log = CRMSyncLog(
        lead_id=lead_id,
        crm_provider=request.crm_provider,
        sync_type=sync_type,
        status=sync_status,
        payload=payload,
        error_message=error_message,
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    return sync_log


@router.get("/logs/{lead_id}", response_model=list[CRMSyncLogResponse])
def get_lead_crm_logs(lead_id: int, db: DatabaseSession) -> list[CRMSyncLog]:
    """Return CRM sync history for a lead, newest attempt first."""
    if db.get(Lead, lead_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    statement = (
        select(CRMSyncLog)
        .where(CRMSyncLog.lead_id == lead_id)
        .order_by(CRMSyncLog.synced_at.desc(), CRMSyncLog.log_id.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/status", response_model=CRMStatusResponse)
def get_crm_status(db: DatabaseSession) -> CRMStatusResponse:
    """Report simulated provider connectivity and the last 24-hour failure rate."""
    since = datetime.now(timezone.utc) - timedelta(hours=RECENT_WINDOW_HOURS)
    recent_syncs = db.scalar(
        select(func.count(CRMSyncLog.log_id)).where(CRMSyncLog.synced_at >= since)
    ) or 0
    recent_failures = db.scalar(
        select(func.count(CRMSyncLog.log_id)).where(
            CRMSyncLog.synced_at >= since,
            CRMSyncLog.status == "failed",
        )
    ) or 0
    failure_rate = recent_failures / recent_syncs if recent_syncs else 0.0
    return CRMStatusResponse(
        connectivity="simulated",
        recent_window_hours=RECENT_WINDOW_HOURS,
        recent_syncs=recent_syncs,
        recent_failures=recent_failures,
        failure_rate=round(failure_rate, 4),
        providers={"salesforce": "simulated", "hubspot": "simulated"},
    )
