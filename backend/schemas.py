"""Pydantic request/response models for the public API.

Response shapes intentionally match the contract documented in
``docs/api-contract.md`` and expected by the Streamlit frontend
(``docs/backend_api_contract.md`` in the AI repository): lead identifiers are
serialised as strings and the lifecycle field is exposed as ``stage``.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from backend.db import LIFECYCLE_STAGES, STAGE_ALIASES

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

StageLiteral = Literal[
    "prospecting", "discovery", "qualified", "proposal", "negotiation", "converted", "lost"
]
RoleLiteral = Literal["admin", "manager", "rep", "viewer"]


def normalise_stage(value: str | None) -> str:
    """Map UI aliases (``Qualified``, ``Closed Won``, ...) onto canonical names."""
    if value is None:
        return "prospecting"
    key = str(value).strip().lower().replace("_", " ").replace("-", " ")
    key = re.sub(r"\s+", " ", key)
    key = STAGE_ALIASES.get(key, key)
    if key not in LIFECYCLE_STAGES:
        raise ValueError(
            "Invalid lifecycle stage. Allowed: " + ", ".join(LIFECYCLE_STAGES)
        )
    return key


def derived_status(stage: str) -> str:
    """Presentation-only status derived from the canonical lifecycle stage."""
    if stage in {"converted", "lost"}:
        return "Closed"
    if stage in {"qualified", "proposal", "negotiation"}:
        return "Active"
    return "New"


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
class LeadBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=240)
    industry: str = Field(default="", max_length=160)
    contact_name: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=320)
    phone: str = Field(default="", max_length=80)
    website: str = Field(default="", max_length=500)
    company_size: str = Field(default="", max_length=100)
    annual_revenue: str = Field(default="", max_length=100)
    funding_stage: str = Field(default="", max_length=100)
    tech_stack: str = Field(default="", max_length=4000)
    company_description: str = Field(default="", max_length=8000)
    prospect_role: str = Field(default="", max_length=120)
    engagement_history: str = Field(default="", max_length=8000)
    explicit_needs: str = Field(default="", max_length=8000)
    response_behavior: str = Field(default="", max_length=4000)
    user_research: str = Field(default="", max_length=8000)
    pain_points: str = Field(default="", max_length=8000)
    lead_source: str = Field(default="", max_length=120)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value and not _EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("website")
    @classmethod
    def _valid_website(cls, value: str) -> str:
        value = (value or "").strip()
        if value and "://" not in value:
            value = "https://" + value
        if value and not re.match(r"^https?://[^\s/]+\.[^\s/]+", value):
            raise ValueError("Enter a valid website URL.")
        return value

    @field_validator("company_name")
    @classmethod
    def _clean_company(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", (value or "").strip())
        if not cleaned:
            raise ValueError("Company name is required.")
        return cleaned


class LeadCreate(LeadBase):
    stage: str | None = None
    #: Legacy field accepted for backwards compatibility; ``stage`` wins.
    status: str | None = None

    @model_validator(mode="after")
    def _resolve_stage(self) -> "LeadCreate":
        chosen = self.stage or self.status or "prospecting"
        object.__setattr__(self, "stage", normalise_stage(chosen))
        return self


class LeadUpdate(BaseModel):
    """Partial update. Every field is optional; unset fields are untouched."""

    company_name: str | None = Field(default=None, min_length=1, max_length=240)
    industry: str | None = Field(default=None, max_length=160)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    company_size: str | None = Field(default=None, max_length=100)
    annual_revenue: str | None = Field(default=None, max_length=100)
    funding_stage: str | None = Field(default=None, max_length=100)
    tech_stack: str | None = Field(default=None, max_length=4000)
    company_description: str | None = Field(default=None, max_length=8000)
    prospect_role: str | None = Field(default=None, max_length=120)
    engagement_history: str | None = Field(default=None, max_length=8000)
    explicit_needs: str | None = Field(default=None, max_length=8000)
    response_behavior: str | None = Field(default=None, max_length=4000)
    user_research: str | None = Field(default=None, max_length=8000)
    pain_points: str | None = Field(default=None, max_length=8000)
    lead_source: str | None = Field(default=None, max_length=120)
    stage: str | None = None
    status: str | None = None

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if value and not _EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("website")
    @classmethod
    def _valid_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if value and "://" not in value:
            value = "https://" + value
        if value and not re.match(r"^https?://[^\s/]+\.[^\s/]+", value):
            raise ValueError("Enter a valid website URL.")
        return value

    @field_validator("stage")
    @classmethod
    def _stage(cls, value: str | None) -> str | None:
        return None if value is None else normalise_stage(value)


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    industry: str
    contact_name: str
    email: str
    phone: str
    website: str
    company_size: str
    annual_revenue: str
    funding_stage: str
    tech_stack: str
    company_description: str
    prospect_role: str
    engagement_history: str
    explicit_needs: str
    response_behavior: str
    user_research: str
    pain_points: str
    lead_source: str
    stage: str
    status: str
    owner_id: int | None = None
    created_at: datetime
    updated_at: datetime


class ImportRowError(BaseModel):
    row: int
    error: str


class ImportReport(BaseModel):
    filename: str
    imported: int
    duplicates: int
    invalid: int
    total_rows: int
    errors: list[ImportRowError] = Field(default_factory=list)
    duplicate_rows: list[int] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def skipped(self) -> int:
        """Rows not imported; provided for the frontend import summary."""
        return self.duplicates + self.invalid


class DuplicateCheckRequest(BaseModel):
    email: str = ""
    company_name: str = ""
    contact_name: str = ""


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    matched_lead_id: str | None = None
    match_reason: str | None = None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(default="", max_length=200)
    password: str = Field(min_length=8, max_length=200)
    role: RoleLiteral = "rep"

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value


# ---------------------------------------------------------------------------
# Intelligence / outreach / scoring / conversations
# ---------------------------------------------------------------------------
class IntelligenceRequest(BaseModel):
    """Optional overrides when requesting company analysis."""

    product_service: str = Field(default="", max_length=500)
    extra_context: str = Field(default="", max_length=8000)


class OutreachRequest(BaseModel):
    lead_id: int
    tone: str = Field(default="professional", max_length=60)
    length: Literal["short", "medium", "long"] = "medium"
    outreach_type: Literal[
        "cold_email", "follow_up", "linkedin_message", "call_script", "short_message"
    ] = "cold_email"
    goal: str = Field(default="start a discovery conversation", max_length=200)
    industry: str = Field(default="", max_length=160)
    pain_points: list[str] = Field(default_factory=list)
    product_service: str = Field(default="", max_length=500)
    call_to_action: str = Field(default="", max_length=500)

    @field_validator("pain_points")
    @classmethod
    def _cap_pain_points(cls, value: list[str]) -> list[str]:
        cleaned = [str(v).strip()[:300] for v in value if str(v).strip()]
        if len(cleaned) > 10:
            raise ValueError("At most 10 pain points may be supplied.")
        return cleaned


class ConversationRequest(BaseModel):
    lead_id: int
    transcript: str = Field(default="", max_length=60000)
    notes: str = Field(default="", max_length=20000)
    interaction_type: Literal["call", "meeting", "demo", "email", "note"] = "call"

    @model_validator(mode="after")
    def _require_content(self) -> "ConversationRequest":
        if not (self.transcript.strip() or self.notes.strip()):
            raise ValueError("Provide a transcript or notes to summarise.")
        return self


class OutreachDraftWrite(BaseModel):
    subject: str = Field(default="", max_length=500)
    body: str = Field(min_length=1, max_length=40000)
    tone: str = Field(default="professional", max_length=60)
    status: Literal["draft", "approved", "sent", "archived"] = "draft"


class OutreachCampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    subject: str
    body: str
    channel: str
    tone: str
    length: str
    outreach_type: str
    goal: str
    industry_context: str = ""
    pain_points_used: list = Field(default_factory=list)
    status: str
    provider: str
    model: str
    created_at: datetime
    updated_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    interaction_type: str
    interaction_date: datetime
    transcript: str
    summary: str
    key_points: list
    action_items: list


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class MetricValue(BaseModel):
    value: float | None
    definition: str
    pending_definition: bool = False


class AnalyticsResponse(BaseModel):
    source: str
    is_demo: bool = False
    generated_at: datetime
    total_leads: int
    qualified_leads: int
    converted_leads: int
    average_lead_score: float | None
    conversion_rate: MetricValue
    pipeline_value: MetricValue
    average_response_time_days: MetricValue
    average_sales_cycle_days: MetricValue
    outreach_activity: int
    interactions_logged: int
    pipeline_distribution: list[dict[str, Any]]
    lead_score_distribution: list[dict[str, Any]]
    activity_trend: list[dict[str, Any]]
    follow_up_tasks: int


class FollowUpItem(BaseModel):
    lead_id: str
    company_name: str
    priority: str
    recommended_action: str
    score: int | None
    last_interaction_at: datetime | None
    reason: str


class ErrorBody(BaseModel):
    detail: str
    errors: list[dict[str, Any]] | None = None
