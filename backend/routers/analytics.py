"""Analytics, follow-ups and CRM integration surface (Modules 5-6)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import CRMSyncLog, Lead, SalesAnalytics, get_db
from backend.deps import Principal, get_current_user, require_manager, require_writer
from backend.errors import ApiError
from backend.intelligence import IntelligenceError, get_engine
from backend.routers._helpers import get_lead_or_404
from backend.schemas import AnalyticsResponse, FollowUpItem
from backend.services.analytics import build_follow_ups, compute_analytics
from backend.services.crm import build_standardized_payload, simulate_sync
from backend.services.leads import lead_to_dict

router = APIRouter(tags=["analytics"])

_CRM_FIELDS = {
    "company_name",
    "contact_name",
    "email",
    "phone",
    "industry",
    "website",
    "company_size",
    "stage",
}


@router.get("/api/v1/analytics", response_model=AnalyticsResponse)
@router.get("/api/v1/dashboard/summary", response_model=AnalyticsResponse, include_in_schema=False)
def analytics(
    _: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> AnalyticsResponse:
    return compute_analytics(db, get_settings())


@router.post("/api/v1/analytics/snapshot", status_code=201)
def create_snapshot(
    _: Principal = Depends(require_manager), db: Session = Depends(get_db)
) -> dict[str, Any]:
    summary = compute_analytics(db, get_settings())
    row = SalesAnalytics(
        total_leads=summary.total_leads,
        qualified_leads=summary.qualified_leads,
        converted_leads=summary.converted_leads,
        conversion_rate=summary.conversion_rate.value,
        pipeline_value=summary.pipeline_value.value,
        average_lead_score=summary.average_lead_score,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "metric_date": row.metric_date.isoformat()}


@router.get("/api/v1/follow-ups", response_model=list[FollowUpItem])
def follow_ups(
    _: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[FollowUpItem]:
    return build_follow_ups(db)


@router.get("/api/v1/recommendations/{lead_id}")
def recommendation(
    lead_id: int,
    _: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    lead = get_lead_or_404(db, lead_id)
    try:
        engine = get_engine()
        result, execution = engine.recommend(lead_to_dict(lead))
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Recommendation failed: {exc}") from exc
    return {"execution": execution.model_dump(), **result.model_dump()}


@router.post("/api/v1/analytics/insights")
def analytics_insights(
    _: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    summary = compute_analytics(db, get_settings())
    payload = summary.model_dump(mode="json")
    try:
        engine = get_engine()
        result, execution = engine.interpret_analytics(payload)
    except IntelligenceError as exc:
        raise ApiError(502, "ai_failed", f"Analytics interpretation failed: {exc}") from exc
    return {"execution": execution.model_dump(), **result.model_dump()}


# ---------------------------------------------------------------------------
# CRM (Module 5, planned integration - SRS D-06)
# ---------------------------------------------------------------------------
@router.get("/api/v1/crm/providers")
def crm_providers(_: Principal = Depends(get_current_user)) -> list[dict[str, Any]]:
    return [
        {
            "provider": "salesforce",
            "configured": bool(os.getenv("SALESFORCE_ACCESS_TOKEN")),
            "live_sync_available": False,
        },
        {
            "provider": "hubspot",
            "configured": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
            "live_sync_available": False,
        },
    ]


@router.post("/api/v1/crm/mappings/validate")
def validate_mapping(
    body: dict[str, Any], _: Principal = Depends(require_writer)
) -> dict[str, Any]:
    mapping = body.get("mapping", body)
    if not isinstance(mapping, dict):
        raise ApiError(422, "invalid_mapping", "mapping must be an object.")
    invalid = [
        key
        for key, value in mapping.items()
        if key not in _CRM_FIELDS or not isinstance(value, str) or not value.strip()
    ]
    return {
        "valid": not invalid,
        "errors": [f"Invalid source field or target: {item}" for item in invalid],
        "mapping": mapping,
    }


@router.post("/api/v1/crm/sync/preview")
def crm_preview(
    body: dict[str, Any],
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ids = body.get("lead_ids", [])
    if not isinstance(ids, list) or len(ids) > 500:
        raise ApiError(422, "invalid_lead_ids", "lead_ids must be a list of at most 500 IDs.")
    records = []
    for item in ids:
        try:
            lead = db.get(Lead, int(item))
        except (TypeError, ValueError):
            lead = None
        if lead is None:
            records.append({"lead_id": item, "valid": False, "error": "Lead not found"})
        else:
            records.append({"lead_id": lead.id, "valid": True, "fields": lead_to_dict(lead)})
    return {
        "provider": body.get("provider"),
        "operation": body.get("operation", "upsert"),
        "dry_run": True,
        "records": records,
    }


@router.post("/api/v1/crm/sync")
def crm_sync(
    body: dict[str, Any],
    principal: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Synchronise leads with a CRM.

    The default remains a truthful ``501`` because no live connector exists
    (SRS D-06).  Passing ``"simulate": true`` runs Doran's provider-neutral
    payload mapping and deterministic simulator, persisting an audit row whose
    ``mode`` is ``simulated``.  A simulation is never reported as a live sync.
    """
    provider = str(body.get("provider", "")).lower()
    if provider not in {"salesforce", "hubspot"}:
        raise ApiError(422, "invalid_provider", "provider must be salesforce or hubspot.")

    operation = str(body.get("operation", "upsert"))[:40]
    simulate = bool(body.get("simulate", False))
    raw_ids = body.get("lead_ids", [])
    if raw_ids is None:
        raw_ids = []
    if not isinstance(raw_ids, list):
        raise ApiError(422, "invalid_lead_ids", "lead_ids must be a list.")
    if simulate:
        if not raw_ids:
            raise ApiError(422, "invalid_lead_ids", "Provide at least one lead_id to simulate.")
        if len(raw_ids) > 500:
            raise ApiError(422, "invalid_lead_ids", "lead_ids must contain at most 500 IDs.")

        records: list[dict[str, Any]] = []
        log_ids: list[int] = []
        for item in raw_ids:
            try:
                lead = db.get(Lead, int(item))
            except (TypeError, ValueError):
                lead = None
            if lead is None:
                records.append({"lead_id": item, "status": "failed", "error": "Lead not found"})
                continue

            payload = build_standardized_payload(lead, operation)
            result = simulate_sync(provider, payload)
            log = CRMSyncLog(
                lead_id=lead.id,
                provider=provider,
                operation=operation,
                status=str(result["status"]),
                external_record_id=str(result.get("external_record_id") or ""),
                request_metadata={
                    "mode": "simulated",
                    "requested_by": principal.email,
                    "payload": payload,
                },
                response_metadata={
                    "mode": "simulated",
                    "status": result["status"],
                    "simulated": True,
                },
                error_message=str(result.get("error_message") or ""),
            )
            db.add(log)
            db.flush()
            log_ids.append(log.id)
            records.append(
                {
                    "lead_id": lead.id,
                    "status": result["status"],
                    "external_record_id": result.get("external_record_id"),
                    "payload": payload,
                    "error": result.get("error_message"),
                }
            )
        db.commit()
        failed = sum(1 for record in records if record["status"] != "success")
        return {
            "provider": provider,
            "operation": operation,
            "mode": "simulated",
            "simulated": True,
            "status": "success" if failed == 0 else "partial",
            "records": records,
            "sync_log_ids": log_ids,
            "note": (
                "Simulated CRM synchronisation. No Salesforce or HubSpot request was made; "
                "payloads and audit rows are locally generated for demonstration."
            ),
        }

    log = CRMSyncLog(
        provider=provider,
        operation=operation,
        status="failed",
        request_metadata={
            "mode": "not_configured",
            "requested_by": principal.email,
            "lead_ids": raw_ids,
        },
        error_message="Live CRM transport is not configured in this build.",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    raise ApiError(
        501,
        "crm_not_configured",
        "The CRM adapter transport is not configured. A failed synchronisation attempt "
        "was recorded in the sync log (SRS D-06).",
        meta={"sync_log_id": log.id},
    )


@router.get("/api/v1/crm/status")
def crm_status(
    _: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Report CRM connectivity mode and 24-hour simulated-sync health.

    Endpoint pattern adapted from M Doran's ``GET /crm/status`` (team-c-doran).
    """
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_syncs = db.scalar(
        select(func.count(CRMSyncLog.id)).where(CRMSyncLog.created_at >= since)
    ) or 0
    recent_failures = db.scalar(
        select(func.count(CRMSyncLog.id)).where(
            CRMSyncLog.created_at >= since,
            CRMSyncLog.status == "failed",
        )
    ) or 0
    return {
        "connectivity": "simulated",
        "live_transport_available": False,
        "recent_window_hours": 24,
        "recent_syncs": int(recent_syncs),
        "recent_failures": int(recent_failures),
        "failure_rate": round(recent_failures / recent_syncs, 4) if recent_syncs else 0.0,
        "providers": {
            "salesforce": "simulated" if os.getenv("SALESFORCE_ACCESS_TOKEN") else "not_configured",
            "hubspot": "simulated" if os.getenv("HUBSPOT_ACCESS_TOKEN") else "not_configured",
        },
        "note": (
            "Live CRM transport is not implemented (SRS D-06). The simulator builds a "
            "provider-neutral payload and records the attempt; it does not contact a CRM."
        ),
    }


@router.get("/api/v1/crm/sync-logs")
def sync_logs(
    _: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    rows = db.scalars(select(CRMSyncLog).order_by(CRMSyncLog.id.desc()).limit(250)).all()
    return [
        {
            "id": row.id,
            "lead_id": row.lead_id,
            "provider": row.provider,
            "operation": row.operation,
            "status": row.status,
            "error_message": row.error_message,
            "attempt_count": row.attempt_count,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/api/v1/crm/sync-logs/{log_id}/retry")
def retry_sync(
    log_id: int,
    _: Principal = Depends(require_writer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    log = db.get(CRMSyncLog, log_id)
    if log is None:
        raise ApiError(404, "sync_log_not_found", f"Sync log {log_id} was not found.")
    if log.status == "success":
        raise ApiError(409, "already_succeeded", "Successful CRM operations cannot be retried.")
    log.attempt_count += 1
    log.status = "failed"
    log.error_message = "Retry unavailable: CRM adapter transport is not configured."
    db.commit()
    return {
        "id": log.id,
        "status": log.status,
        "attempt_count": log.attempt_count,
        "error_message": log.error_message,
    }
