"""Pydantic contracts for the AI/ML layer.

One definition of each payload means the service output, the persistence layer
and the tests can never drift apart — and any consumer (API, UI, worker) binds to
the same shape.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sales_intel.utils import utcnow


# ===========================================================================
# Leads / features  (input side of scoring)
# ===========================================================================
class LeadFeatures(BaseModel):
    """Raw signals available in the DB for a single lead."""

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    company_name: str = ""
    industry: str = ""

    # engagement
    email_opens: int = 0
    email_clicks: int = 0
    email_replies: int = 0
    inbound_replies: int = 0
    meetings_held: int = 0
    call_connect_rate: float = 0.0
    avg_response_latency_hours: float = 72.0

    # fit
    industry_match: float = 0.0
    company_size_score: float = 0.0
    seniority_score: float = 0.0
    tech_stack_overlap: float = 0.0
    budget_potential_usd: float = 0.0

    # intent
    pricing_page_visits: int = 0
    demo_requests: int = 0
    content_downloads: int = 0
    hiring_signal: int = 0
    competitor_mention: int = 0

    # decision readiness
    budget_confirmed: int = 0
    timeline_months: int = 12
    stakeholders_identified: int = 0
    procurement_stage: int = 0
    champion_identified: int = 0


class LeadScore(BaseModel):
    lead_id: str
    score: float = Field(ge=0, le=100)
    band: Literal["Hot", "Warm", "Cold"]
    conversion_probability: float = Field(ge=0, le=1)
    subscores: dict[str, float]
    drivers: list[dict[str, Any]]
    model_version: str
    scored_at: datetime = Field(default_factory=utcnow)


# ===========================================================================
# Next-Best-Action  (Day 15)
# ===========================================================================
class InteractionHistory(BaseModel):
    channel: Literal["email", "call", "linkedin", "whatsapp", "meeting", "none"]
    occurred_at: datetime
    outcome: Literal["no_response", "opened", "replied", "positive", "negative", "meeting_booked"] = "no_response"


class LeadContext(BaseModel):
    """Everything the NBA engine needs beyond the raw feature vector."""

    model_config = ConfigDict(extra="forbid")

    lead_id: str
    company_name: str = ""
    industry: str = ""
    lifecycle_stage: Literal[
        "new", "contacted", "qualified", "proposal", "negotiation", "won", "lost", "nurture"
    ] = "new"
    owner_role: str = "Account Executive"
    seniority: Literal["c_level", "vp", "director", "manager", "unknown"] = "unknown"
    decision_maker: bool = False
    deal_value_usd: float = 0.0
    timezone: str = "Asia/Kolkata"
    last_contact_at: datetime | None = None
    history: list[InteractionHistory] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)
    do_not_contact: bool = False
    local_hour: int | None = None
    transcript: str | None = Field(
        default=None,
        description="Optional speaker-labelled transcript; the agent summarises it "
                    "and folds the outcome into the recommendation.",
    )


class Touch(BaseModel):
    step: int
    offset_days: int
    channel: Literal["email", "call", "linkedin", "whatsapp", "meeting"]
    purpose: str
    planned_at: date


class ChannelAllocation(BaseModel):
    channel: str
    share: int                     # percentage, sums to 100
    rationale: str


class ContentStrategy(BaseModel):
    content_type: str
    angle: str
    key_messages: list[str]
    suggested_asset: str
    call_to_action: str
    tone: str
    personalisation_hooks: list[str]


class NextBestAction(BaseModel):
    lead_id: str
    priority: Literal["P0", "P1", "P2", "P3"]
    priority_score: float
    recommended_channel: Literal["email", "call", "linkedin", "whatsapp", "meeting"]
    next_touch_date: date
    days_since_last_contact: int | None
    cadence: list[Touch]
    channel_mix: list[ChannelAllocation]
    content: ContentStrategy
    rationale: list[str]
    risk_flags: list[str]
    suppress: bool = False
    suppress_reason: str | None = None
    generated_at: datetime = Field(default_factory=utcnow)


# ===========================================================================
# Conversation summarisation  (Day 24)
# ===========================================================================
class Utterance(BaseModel):
    speaker: str
    text: str
    timestamp: datetime | None = None
    is_internal: bool = Field(
        default=False,
        description="True when the speaker belongs to the selling team.",
    )


class ActionItem(BaseModel):
    task: str
    owner: str = "unassigned"
    owner_side: Literal["internal", "customer", "unassigned"] = "unassigned"
    due_date: date | None = None
    due_hint: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    source_quote: str = ""


class DiscussionPoint(BaseModel):
    topic: str
    detail: str
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    quote: str = ""


class ConversationSummary(BaseModel):
    interaction_id: str
    lead_id: str | None = None
    summary: str
    key_discussion_points: list[DiscussionPoint]
    action_items: list[ActionItem]
    decisions: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    competitors_mentioned: list[str] = Field(default_factory=list)
    next_step: str = ""
    overall_sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    talk_ratio_internal: float = 0.0
    confidence: float = 0.0
    engine: Literal["llm", "heuristic"] = "heuristic"
    model: str = ""
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("summary")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        return v.strip() or "No content could be summarised."


# ===========================================================================
# Request / response envelopes for the API
# ===========================================================================
class ScoreRequest(BaseModel):
    lead: LeadFeatures
    persist: bool = True


class NBARequest(BaseModel):
    lead: LeadFeatures
    context: LeadContext
    persist: bool = True


class SummarizeRequest(BaseModel):
    interaction_id: str
    lead_id: str | None = None
    utterances: list[Utterance]
    meeting_started_at: datetime | None = None
    persist: bool = True


class SummarizeResponse(BaseModel):
    summary: ConversationSummary
    action_items_persisted: int = 0
