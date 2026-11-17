"""Request and response schemas for CRM synchronization."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CRMProvider = Literal["salesforce", "hubspot"]
CRMSyncAction = Literal["sync_contact", "update_stage", "activity_log"]
CRMSyncStatus = Literal["success", "failed"]


class CRMSyncRequest(BaseModel):
    """CRM provider and synchronization operation requested for a lead."""

    crm_provider: CRMProvider
    action: CRMSyncAction


class CRMSyncLogResponse(BaseModel):
    """Persisted CRM synchronization attempt."""

    model_config = ConfigDict(from_attributes=True)

    log_id: int
    lead_id: int
    crm_provider: str
    sync_type: str
    status: CRMSyncStatus
    payload: dict[str, object]
    error_message: str | None
    synced_at: datetime


class CRMStatusResponse(BaseModel):
    """Connectivity mode and recent CRM synchronization health."""

    connectivity: Literal["simulated"]
    recent_window_hours: int = Field(gt=0)
    recent_syncs: int = Field(ge=0)
    recent_failures: int = Field(ge=0)
    failure_rate: float = Field(ge=0.0, le=1.0)
    providers: dict[str, Literal["simulated"]]
