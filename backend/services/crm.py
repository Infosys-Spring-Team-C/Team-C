"""Provider-neutral CRM payload mapping and a clearly-labelled sync simulator.

Adapted from M Doran's backend work (``team-c-doran``: ``app/services/crm_service.py``)
and merged into the canonical Team-C backend.  Doran's original contract mapped
``sync_contact`` / ``update_stage`` / ``activity_log`` actions onto a
provider-neutral record and simulated the transport when no connector was
configured.  This version keeps that design but reads the canonical ``Lead``
model and never claims a live CRM call.

No module here performs network I/O.  ``simulate_sync`` is a deterministic
stand-in used for demonstration and for contract tests; a real connector can
replace it without changing the API surface.
"""
from __future__ import annotations

import hashlib
from typing import Any, Literal

from backend.db import Lead

CRMAction = Literal["upsert", "sync_contact", "update_stage", "activity_log"]

#: Canonical operation -> the CRM record type it produces.
ACTION_TO_RECORD_TYPE: dict[str, str] = {
    "upsert": "contact",
    "sync_contact": "contact",
    "update_stage": "deal",
    "activity_log": "activity",
}


def build_standardized_payload(lead: Lead, action: str = "upsert") -> dict[str, Any]:
    """Map a canonical lead onto the provider-neutral CRM record shape.

    Mirrors Doran's ``build_standardized_payload`` while using the canonical
    column names (``lifecycle_stage``, ``annual_revenue``, ``owner_id``).
    """
    record_type = ACTION_TO_RECORD_TYPE.get(action, "contact")
    common: dict[str, Any] = {
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "phone": lead.phone,
        "industry": lead.industry,
        "website": lead.website,
        "company_size": lead.company_size,
        "annual_revenue": lead.annual_revenue,
        "lifecycle_stage": lead.lifecycle_stage,
        "owner_id": lead.owner_id,
    }
    if record_type == "deal":
        return {
            "record_type": "deal",
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "stage": lead.lifecycle_stage,
            "annual_revenue": lead.annual_revenue,
        }
    if record_type == "activity":
        return {
            "record_type": "activity",
            **common,
            "activity": "SalesGenie lead synchronisation",
        }
    return {"record_type": "contact", **common}


def simulate_sync(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic simulated provider response.

    Deliberately does not pretend to be a live Salesforce/HubSpot call.  The
    caller persists ``mode=simulated`` in the audit log so the UI and the report
    can distinguish a simulation from a configured transport.
    """
    missing = [key for key in ("company_name", "contact_name") if not str(payload.get(key) or "").strip()]
    if missing:
        return {
            "status": "failed",
            "mode": "simulated",
            "error_message": f"Missing required CRM fields: {', '.join(missing)}.",
            "external_record_id": "",
        }
    digest = hashlib.sha1(
        f"{provider}:{payload.get('company_name')}:{payload.get('contact_name')}".encode("utf-8")
    ).hexdigest()[:10]
    return {
        "status": "success",
        "mode": "simulated",
        "error_message": None,
        "external_record_id": f"sim-{provider}-{digest}",
    }
