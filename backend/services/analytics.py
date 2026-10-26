"""Analytics and follow-up computation.

KPI definitions follow SRS FR-046 .. FR-053.  Only definitions the schema can
actually support are computed; metrics whose definition is still an open team
decision (SRS D-10) are returned as ``null`` with ``pending_definition=true``
rather than being filled with an invented number.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.db import (
    LIFECYCLE_STAGES,
    TERMINAL_STAGES,
    Lead,
    LeadScore,
    OutreachCampaign,
    SalesInteraction,
    utcnow,
)
from backend.schemas import AnalyticsResponse, FollowUpItem, MetricValue

QUALIFIED_STAGES = {"qualified", "proposal", "negotiation"}

CONVERSION_RATE_DEFINITION = (
    "converted_leads / total_leads, computed over all stored leads. "
    "Proposed definition for SRS D-10 - pending team approval."
)
PENDING_VALUE = "No field in the current schema supports this metric; SRS D-10 is unresolved."
PENDING_RESPONSE = (
    "No response timestamps are stored, so average response time cannot be computed. SRS D-10."
)
PENDING_CYCLE = (
    "No won/lost transition timestamps are stored, so average sales cycle cannot be "
    "computed. SRS D-10."
)


def latest_score_ids():
    return (
        select(func.max(LeadScore.id).label("id"))
        .group_by(LeadScore.lead_id)
        .subquery()
    )


def compute_analytics(db: Session, settings: Settings) -> AnalyticsResponse:
    leads = db.scalars(select(Lead)).all()
    total = len(leads)
    qualified = sum(1 for lead in leads if lead.lifecycle_stage in QUALIFIED_STAGES)
    converted = sum(1 for lead in leads if lead.lifecycle_stage == "converted")

    latest = latest_score_ids()
    scores = list(
        db.scalars(select(LeadScore.score).where(LeadScore.id.in_(select(latest.c.id)))).all()
    )
    average_score = round(sum(scores) / len(scores), 1) if scores else None

    stage_counts = Counter(lead.lifecycle_stage for lead in leads)
    pipeline = [
        {"stage": stage, "count": stage_counts.get(stage, 0)}
        for stage in LIFECYCLE_STAGES
    ]

    bands = {"0-44": 0, "45-69": 0, "70-100": 0}
    for score in scores:
        if score >= 70:
            bands["70-100"] += 1
        elif score >= 45:
            bands["45-69"] += 1
        else:
            bands["0-44"] += 1
    score_distribution = [{"band": band, "count": count} for band, count in bands.items()]

    today = utcnow().date()
    trend: list[dict[str, Any]] = []
    for offset in range(13, -1, -1):
        day = today - timedelta(days=offset)
        created = sum(1 for lead in leads if lead.created_at and lead.created_at.date() == day)
        trend.append({"date": day.isoformat(), "activity": created})

    follow_ups = build_follow_ups(db)

    return AnalyticsResponse(
        source="database",
        is_demo=False,
        generated_at=utcnow(),
        total_leads=total,
        qualified_leads=qualified,
        converted_leads=converted,
        average_lead_score=average_score,
        conversion_rate=MetricValue(
            value=round(converted / total, 4) if total else None,
            definition=CONVERSION_RATE_DEFINITION,
        ),
        pipeline_value=MetricValue(
            value=None, definition=PENDING_VALUE, pending_definition=True
        ),
        average_response_time_days=MetricValue(
            value=None, definition=PENDING_RESPONSE, pending_definition=True
        ),
        average_sales_cycle_days=MetricValue(
            value=None, definition=PENDING_CYCLE, pending_definition=True
        ),
        outreach_activity=db.scalar(select(func.count()).select_from(OutreachCampaign)) or 0,
        interactions_logged=db.scalar(select(func.count()).select_from(SalesInteraction)) or 0,
        pipeline_distribution=pipeline,
        lead_score_distribution=score_distribution,
        activity_trend=trend,
        follow_up_tasks=len(follow_ups),
    )


def build_follow_ups(db: Session, limit: int = 20) -> list[FollowUpItem]:
    """Derive the follow-up panel from persisted Module 4 output.

    AC-029 requires the panel to show recommendations derived from M4 output, so
    only leads that already have a stored score are included.  Nothing is
    generated on the fly here.
    """
    latest = latest_score_ids()
    rows = db.execute(
        select(LeadScore, Lead)
        .join(Lead, Lead.id == LeadScore.lead_id)
        .where(LeadScore.id.in_(select(latest.c.id)))
        .order_by(LeadScore.score.desc())
        .limit(limit)
    ).all()

    interaction_dates = dict(
        db.execute(
            select(SalesInteraction.lead_id, func.max(SalesInteraction.interaction_date))
            .group_by(SalesInteraction.lead_id)
        ).all()
    )

    items: list[FollowUpItem] = []
    for score, lead in rows:
        if lead.lifecycle_stage in TERMINAL_STAGES:
            continue
        items.append(
            FollowUpItem(
                lead_id=str(lead.id),
                company_name=lead.company_name,
                priority=score.priority_level,
                recommended_action=score.recommended_next_action,
                score=score.score,
                last_interaction_at=interaction_dates.get(lead.id),
                reason=f"Latest stored score {score.score}/100 ({score.model_version}).",
            )
        )
    return items
