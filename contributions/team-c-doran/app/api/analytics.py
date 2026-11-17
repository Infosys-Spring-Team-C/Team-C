"""SQL aggregation endpoints for Streamlit dashboard KPIs."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import (
    LeadOverview,
    LeadPriority,
    PipelineValueResponse,
    PriorityPipelineValue,
    TopLead,
)
from database.models import Lead, LeadScore

router = APIRouter(prefix="/analytics", tags=["analytics"])
DatabaseSession = Annotated[Session, Depends(get_db)]
LEAD_STATUSES = ("new", "contacted", "qualified", "closed")
LEAD_PRIORITIES: tuple[LeadPriority, ...] = ("high", "medium", "low")


@router.get("/overview", response_model=LeadOverview)
def get_analytics_overview(db: DatabaseSession) -> LeadOverview:
    """Return total leads, lifecycle counts, and qualified-or-closed conversion rate."""
    count_columns = [
        func.coalesce(
            func.sum(case((Lead.lead_status == lead_status, 1), else_=0)),
            0,
        ).label(lead_status)
        for lead_status in LEAD_STATUSES
    ]
    row = db.execute(
        select(func.count(Lead.lead_id).label("total_leads"), *count_columns)
    ).one()
    total_leads = int(row.total_leads or 0)
    status_breakdown = {
        lead_status: int(getattr(row, lead_status) or 0)
        for lead_status in LEAD_STATUSES
    }
    converted_count = status_breakdown["qualified"] + status_breakdown["closed"]
    conversion_rate = converted_count / total_leads * 100 if total_leads else 0.0
    return LeadOverview(
        total_leads=total_leads,
        status_breakdown=status_breakdown,
        conversion_rate_percent=round(conversion_rate, 2),
    )


@router.get("/pipeline-value", response_model=PipelineValueResponse)
def get_pipeline_value(db: DatabaseSession) -> PipelineValueResponse:
    """Estimate open pipeline as lead revenue multiplied by AI conversion probability.

    Closed leads are excluded. Because the data model has no deal amount, annual
    company revenue is used as a proxy and results are grouped by AI priority.
    """
    estimated_value = func.coalesce(Lead.revenue, 0.0) * LeadScore.conversion_probability
    statement = (
        select(
            LeadScore.priority_level.label("priority_level"),
            func.count(LeadScore.score_id).label("lead_count"),
            func.coalesce(func.sum(estimated_value), 0.0).label("estimated_value"),
        )
        .join(Lead, Lead.lead_id == LeadScore.lead_id)
        .where(Lead.lead_status != "closed")
        .group_by(LeadScore.priority_level)
    )
    grouped_values: dict[str, PriorityPipelineValue] = {
        priority: PriorityPipelineValue(lead_count=0, estimated_value=0.0)
        for priority in LEAD_PRIORITIES
    }
    for row in db.execute(statement):
        if row.priority_level in grouped_values:
            grouped_values[row.priority_level] = PriorityPipelineValue(
                lead_count=int(row.lead_count),
                estimated_value=round(float(row.estimated_value or 0.0), 2),
            )

    total = sum(group.estimated_value for group in grouped_values.values())
    return PipelineValueResponse(
        total_pipeline_value=round(total, 2),
        by_priority=cast(dict[LeadPriority, PriorityPipelineValue], grouped_values),
    )


@router.get("/top-leads", response_model=list[TopLead])
def get_top_leads(db: DatabaseSession) -> list[TopLead]:
    """Return up to ten leads with the highest current AI scores."""
    statement = (
        select(
            Lead.lead_id,
            Lead.company_name,
            Lead.industry,
            Lead.contact_name,
            Lead.lead_status,
            Lead.revenue,
            LeadScore.lead_score,
            LeadScore.conversion_probability,
            LeadScore.priority_level,
        )
        .join(LeadScore, LeadScore.lead_id == Lead.lead_id)
        .order_by(LeadScore.lead_score.desc(), LeadScore.calculated_at.desc())
        .limit(10)
    )
    return [TopLead.model_validate(row._mapping) for row in db.execute(statement)]
