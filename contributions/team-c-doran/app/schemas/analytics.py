"""Response schemas for dashboard analytics."""

from typing import Literal

from pydantic import BaseModel, Field

LeadPriority = Literal["high", "medium", "low"]


class LeadOverview(BaseModel):
    """Lead volume, lifecycle counts, and conversion rate."""

    total_leads: int = Field(ge=0)
    status_breakdown: dict[str, int]
    conversion_rate_percent: float = Field(ge=0.0, le=100.0)


class PriorityPipelineValue(BaseModel):
    """Estimated value and lead count for one priority group."""

    lead_count: int = Field(ge=0)
    estimated_value: float = Field(ge=0.0)


class PipelineValueResponse(BaseModel):
    """Estimated open pipeline value grouped by lead priority."""

    total_pipeline_value: float = Field(ge=0.0)
    by_priority: dict[LeadPriority, PriorityPipelineValue]


class TopLead(BaseModel):
    """Lead profile and current AI score included in the leaderboard."""

    lead_id: int
    company_name: str
    industry: str
    contact_name: str
    lead_status: str
    revenue: float | None
    lead_score: int
    conversion_probability: float
    priority_level: LeadPriority
