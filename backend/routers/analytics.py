"""Analytics, follow-ups and CRM integration surface (Modules 5-6)."""
from __future__ import annotations

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
from backend.services.crm import (
    ACTION_TO_RECORD_TYPE,
    SUPPORTED_OPERATIONS,
    build_standardized_payload,
    field_mappings,
    simulate_sync,
)
from backend.services.crm_transport import (
    CRMTransportError,
    credentials_present,
    send_with_retry,
    transport_for,
)
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
    "annual_revenue",
    "lifecycle_stage",
    "stage",
    "owner_id",
    "activity",
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
            "provider": provider,
            "configured": credentials_present(provider),
            "live_sync_available": transport_for(provider) is not None,
        }
        for provider in ("salesforce", "hubspot")
    ]


@router.get("/api/v1/crm/field-mappings")
def crm_field_mappings(
    provider: str | None = None,
    _: Principal = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the documented canonical-to-CRM field map.

    The map is descriptive: it is used by the simulator and by the live
    transport, which applies the documented vendor field names. A live request
    is only made when ``CRM_LIVE_ENABLED=true`` and provider credentials are
    configured; otherwise the simulator path is used (SRS D-06).
    """
    try:
        return {
            "mappings": field_mappings(provider),
            "supported_operations": list(SUPPORTED_OPERATIONS),
            "live_transport_available": any(
                transport_for(name) is not None for name in ("salesforce", "hubspot")
            ),
        }
    except ValueError as exc:
        raise ApiError(422, "invalid_provider", str(exc)) from exc


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

    Three outcomes, in order:

    * ``"simulate": true`` runs the provider-neutral mapper and deterministic
      simulator and writes an audit row whose ``mode`` is ``simulated``.
    * A configured live transport (``CRM_LIVE_ENABLED=true`` plus provider
      credentials) sends the mapped record to Salesforce or HubSpot and writes
      a ``mode: live`` audit row per attempt.
    * Otherwise the request is refused with ``501`` and a failed audit row,
      because no connector is configured (SRS D-06).

    A simulation is never reported as a live sync.
    """
    provider = str(body.get("provider", "")).lower()
    if provider not in {"salesforce", "hubspot"}:
        raise ApiError(422, "invalid_provider", "provider must be salesforce or hubspot.")

    operation = str(body.get("operation", "upsert"))[:40]
    if operation not in SUPPORTED_OPERATIONS:
        raise ApiError(
            422,
            "invalid_operation",
            f"operation must be one of: {', '.join(SUPPORTED_OPERATIONS)}.",
        )
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
                entity_type=ACTION_TO_RECORD_TYPE.get(operation, "contact"),
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

    transport = transport_for(provider)
    if transport is not None:
        if not raw_ids:
            raise ApiError(
                422, "invalid_lead_ids", "Provide at least one lead_id to synchronise."
            )
        if len(raw_ids) > 500:
            raise ApiError(422, "invalid_lead_ids", "lead_ids must contain at most 500 IDs.")

        record_type = ACTION_TO_RECORD_TYPE.get(operation, "contact")
        live_records: list[dict[str, Any]] = []
        live_log_ids: list[int] = []
        for item in raw_ids:
            try:
                lead = db.get(Lead, int(item))
            except (TypeError, ValueError):
                lead = None
            if lead is None:
                live_records.append(
                    {"lead_id": item, "status": "failed", "error": "Lead not found"}
                )
                continue

            payload = build_standardized_payload(lead, operation)
            log = CRMSyncLog(
                lead_id=lead.id,
                provider=provider,
                entity_type=record_type,
                operation=operation,
                status="pending",
                request_metadata={
                    "mode": "live",
                    "requested_by": principal.email,
                    "payload": payload,
                },
            )
            db.add(log)
            db.flush()
            live_log_ids.append(log.id)
            try:
                result = send_with_retry(transport, record_type, payload)
            except CRMTransportError as exc:
                log.status = "failed"
                log.attempt_count = max(1, int(exc.attempts or 1))
                log.error_message = str(exc)[:2000]
                log.response_metadata = {
                    "mode": "live",
                    "status": "failed",
                    "http_status": exc.status_code,
                    "attempts": log.attempt_count,
                }
                live_records.append(
                    {
                        "lead_id": lead.id,
                        "status": "failed",
                        "error": str(exc),
                        "http_status": exc.status_code,
                        "attempts": log.attempt_count,
                    }
                )
                continue

            log.status = "success"
            log.external_record_id = str(result.get("external_record_id") or "")
            log.error_message = ""
            log.attempt_count = max(1, int(result.get("attempts") or 1))
            log.response_metadata = {
                "mode": "live",
                "status": "success",
                "http_status": result.get("http_status"),
                "attempts": log.attempt_count,
            }
            live_records.append(
                {
                    "lead_id": lead.id,
                    "status": "success",
                    "external_record_id": log.external_record_id,
                    "http_status": result.get("http_status"),
                    "attempts": log.attempt_count,
                }
            )

        db.commit()
        failed = sum(1 for record in live_records if record["status"] != "success")
        overall = (
            "success"
            if failed == 0
            else ("failed" if failed == len(live_records) else "partial")
        )
        if overall == "failed":
            raise ApiError(
                502,
                "crm_sync_failed",
                "The CRM transport rejected every record. The attempts are recorded "
                "in the sync log; no local lead data was changed.",
                meta={
                    "provider": provider,
                    "operation": operation,
                    "records": live_records,
                    "sync_log_ids": live_log_ids,
                },
            )
        return {
            "provider": provider,
            "operation": operation,
            "mode": "live",
            "simulated": False,
            "status": overall,
            "records": live_records,
            "sync_log_ids": live_log_ids,
            "note": "Records were sent to the configured CRM transport.",
        }

    log = CRMSyncLog(
        provider=provider,
        entity_type=ACTION_TO_RECORD_TYPE.get(operation, "contact"),
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
    """Report CRM connectivity mode and 24-hour sync health.

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
    live = {
        provider: transport_for(provider) is not None
        for provider in ("salesforce", "hubspot")
    }
    return {
        "connectivity": "live" if any(live.values()) else "simulated",
        "live_transport_available": any(live.values()),
        "recent_window_hours": 24,
        "recent_syncs": int(recent_syncs),
        "recent_failures": int(recent_failures),
        "failure_rate": round(recent_failures / recent_syncs, 4) if recent_syncs else 0.0,
        "providers": {
            provider: "live" if configured else "not_configured"
            for provider, configured in live.items()
        },
        "note": (
            "A live transport is configured and enabled for at least one provider."
            if any(live.values())
            else "Live CRM transport is not enabled. The simulator builds a "
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
            "entity_type": row.entity_type,
            "operation": row.operation,
            "status": row.status,
            "external_record_id": row.external_record_id,
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
