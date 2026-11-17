"""CRM payload mapping and local sync simulator."""

from typing import Any, Literal

CRMAction = Literal["sync_contact", "update_stage", "activity_log"]
ACTION_TO_SYNC_TYPE: dict[CRMAction, str] = {
    "sync_contact": "contact_push",
    "update_stage": "deal_update",
    "activity_log": "activity_log",
}


def build_standardized_payload(lead: Any, action: CRMAction) -> dict[str, object]:
    """Map local lead fields to the provider-neutral CRM record shape."""
    common_fields: dict[str, object] = {
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "lead_status": lead.lead_status,
    }
    if action == "sync_contact":
        return {"record_type": "contact", **common_fields}
    if action == "update_stage":
        return {
            "record_type": "deal",
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "stage": lead.lead_status,
        }
    return {
        "record_type": "activity",
        **common_fields,
        "activity": "SalesGenie lead synchronization",
    }


def simulate_crm_sync(
    crm_provider: str, payload: dict[str, object]
) -> dict[str, str | None]:
    """Simulate a successful provider request when no CRM connector is configured."""
    # Keep the provider and exact payload in the call boundary so a real adapter
    # can replace this implementation without changing the API contract.
    _ = crm_provider, payload
    return {"status": "success", "error_message": None}
