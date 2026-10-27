"""Validated boundary models for all outputs shown by the frontend."""
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EvidenceItem(BaseModel):
    statement: str = Field(min_length=1)
    source: str = "User-provided context"
    source_type: Literal["provided", "backend", "transcript", "hypothesis", "analytics"] = "provided"
    confidence: Literal["low", "medium", "high"] = "medium"


class Hypothesis(BaseModel):
    statement: str
    rationale: str
    confidence: Literal["low", "medium", "high"] = "low"
    requires_validation: bool = True


class ResearchResult(BaseModel):
    company_overview: str
    supported_facts: list[EvidenceItem] = Field(default_factory=list)
    potential_challenges: list[Hypothesis] = Field(default_factory=list)
    possible_needs: list[Hypothesis] = Field(default_factory=list)
    opportunities: list[Hypothesis] = Field(default_factory=list)
    product_industry_fit: str
    buyer_role_relevance: str
    qualification_insights: list[str] = Field(default_factory=list)
    discovery_questions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    disclaimer: str = "No website or external company research was performed; conclusions use only supplied context."


class QualificationAssessment(BaseModel):
    category: Literal["Qualified", "Nurture", "Disqualify", "Needs discovery"]
    fit_assessment: str
    buyer_relevance: str
    engagement_assessment: str
    positive_signals: list[str] = Field(default_factory=list)
    risks_or_gaps: list[str] = Field(default_factory=list)
    recommended_next_step: str
    confidence: Literal["low", "medium", "high"] = "low"


class OutreachDraft(BaseModel):
    channel: Literal["Email", "LinkedIn", "Call script", "Short message"]
    subject_line: str | None = None
    body: str = Field(min_length=1)
    call_to_action: str
    personalization_rationale: list[str] = Field(default_factory=list)
    facts_used: list[EvidenceItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    alternative_angle: str | None = None


class ActionItem(BaseModel):
    action: str
    owner: str | None = None
    due_date: str | None = None
    evidence: str
    confidence: Literal["low", "medium", "high"] = "medium"


class ConversationSummary(BaseModel):
    executive_summary: str
    key_discussion_points: list[str] = Field(default_factory=list)
    customer_requirements: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    product_interests: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    competitor_mentions: list[str] = Field(default_factory=list)
    decisions_and_commitments: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    suggested_follow_up: str
    missing_or_uncertain: list[str] = Field(default_factory=list)
    source_note: str = "Extracted only from the supplied transcript and notes."


class Recommendation(BaseModel):
    lead_id: str | None = None
    related_lead: str
    recommended_action: str
    reason: str
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    priority: Literal["High", "Medium", "Low"]
    suggested_timing: str | None = None
    status: Literal["Open", "Completed", "Dismissed"] = "Open"
    follow_up_draft: str | None = None


class SalesInsight(BaseModel):
    title: str
    observation: str
    evidence: str
    confidence: Literal["low", "medium", "high"] = "medium"


class SalesInsightsResult(BaseModel):
    insights: list[SalesInsight] = Field(default_factory=list)
    caveat: str


class ScoreFactor(BaseModel):
    name: str
    weight: float
    normalized_value: float = Field(ge=0, le=1)
    points: float
    explanation: str
    signal: Literal["positive", "negative", "neutral", "missing"]


class LeadScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    qualification_category: Literal["Qualified", "Nurture", "Low priority"]
    factors: list[ScoreFactor]
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_action: str
    methodology_note: str = "This is a configurable heuristic score, not a predicted conversion probability."


class ExecutionRecord(BaseModel):
    operation: str
    provider: str
    model: str
    duration_ms: int
    success: bool
    errors: list[str] = Field(default_factory=list)
    used_mock: bool = False


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    result: Any | None = None
    research: ResearchResult | None = None
    qualification: QualificationAssessment | None = None
    execution: ExecutionRecord
    errors: list[str] = Field(default_factory=list)


class LeadInput(BaseModel):
    id: str | None = None
    company_name: str = ""
    contact_name: str = ""
    email: str = ""
    website: str = ""
    industry: str = ""
    company_size: str = ""
    company_description: str = ""
    prospect_role: str = ""
    status: str = ""
    stage: str = ""
    engagement_history: str = ""
    explicit_needs: str = ""
    response_behavior: str = ""
    user_research: str = ""

    @field_validator("company_name", mode="before")
    @classmethod
    def string_or_empty(cls, v: Any) -> str:
        return "" if v is None else str(v)
