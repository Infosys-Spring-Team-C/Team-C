"""Typed contract between the FastAPI backend and any AI/intelligence engine.

The backend never imports an agent graph or a model SDK directly.  It depends on
the :class:`IntelligenceEngine` protocol and on the Pydantic models in this
module.  Two implementations exist:

* ``backend.intelligence.heuristic`` - deterministic, offline, explainable
  engine shipped with the backend so the API is runnable and testable without
  credentials.  It is explicitly *not* a trained model.
* ``backend.intelligence.external`` - adapter around the reviewed AI package
  (``ai.*`` / ``utils.*``) contributed through its own pull request.

The models mirror the fields the Streamlit frontend consumes, but they are
owned by this repository so the two layers can evolve independently.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]


class EvidenceItem(BaseModel):
    statement: str = Field(min_length=1)
    source: str = "User-provided context"
    source_type: Literal["provided", "backend", "transcript", "hypothesis", "analytics"] = (
        "provided"
    )
    confidence: Confidence = "medium"


class Hypothesis(BaseModel):
    statement: str
    rationale: str
    confidence: Confidence = "low"
    requires_validation: bool = True


class QualificationAssessment(BaseModel):
    category: Literal["Qualified", "Nurture", "Disqualify", "Needs discovery"]
    fit_assessment: str
    buyer_relevance: str
    engagement_assessment: str
    positive_signals: list[str] = Field(default_factory=list)
    risks_or_gaps: list[str] = Field(default_factory=list)
    recommended_next_step: str
    confidence: Confidence = "low"


class LeadIntelligence(BaseModel):
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
    qualification: QualificationAssessment
    confidence: Confidence = "low"
    disclaimer: str = (
        "No website or external company research was performed; conclusions use only "
        "supplied context."
    )


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
    confidence: Confidence = "medium"


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


class ScoreFactor(BaseModel):
    name: str
    weight: float
    normalized_value: float = Field(ge=0, le=1)
    points: float
    explanation: str
    signal: Literal["positive", "negative", "neutral", "missing"]
    #: SRS FR-030 dimension this factor contributes to. ``None`` means the
    #: factor is already a dimension in its own right (offline engine) or the
    #: source did not classify it.
    dimension: Literal["Fit", "Intent", "Engagement", "Decision readiness"] | None = None


class LeadScoreResult(BaseModel):
    score: int = Field(ge=0, le=100)
    qualification_category: Literal["Qualified", "Nurture", "Low priority"]
    factors: list[ScoreFactor]
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_action: str
    #: Populated only by a calibrated model.  Heuristic scoring leaves it empty.
    conversion_probability: float | None = Field(default=None, ge=0, le=1)
    probability_band: Literal["low", "medium", "high"] = "low"
    probability_note: str = (
        "No calibrated conversion model is configured. The band is an uncalibrated "
        "heuristic and must not be read as a statistical probability."
    )
    methodology_note: str = (
        "Configurable heuristic score derived from engagement, fit, intent and "
        "decision readiness. Not a trained or calibrated predictive model."
    )


class SalesInsight(BaseModel):
    title: str
    observation: str
    evidence: str
    confidence: Confidence = "medium"


class SalesInsightsResult(BaseModel):
    insights: list[SalesInsight] = Field(default_factory=list)
    caveat: str


class ExecutionInfo(BaseModel):
    engine: str
    provider: str
    model: str
    duration_ms: int
    used_mock: bool = False
    fallback_reason: str | None = None


class IntelligenceError(RuntimeError):
    """Raised when an AI engine cannot produce a valid, validated result."""


class IntelligenceEngine(Protocol):
    """The only surface the API layer is allowed to depend on."""

    name: str

    def analyze_lead(self, lead: dict[str, Any]) -> tuple[LeadIntelligence, ExecutionInfo]: ...

    def generate_outreach(
        self, lead: dict[str, Any], request: dict[str, Any]
    ) -> tuple[OutreachDraft, ExecutionInfo]: ...

    def summarize_conversation(
        self, transcript: str, notes: str
    ) -> tuple[ConversationSummary, ExecutionInfo]: ...

    def recommend(self, lead: dict[str, Any]) -> tuple[Recommendation, ExecutionInfo]: ...

    def score_lead(self, lead: dict[str, Any]) -> tuple[LeadScoreResult, ExecutionInfo]: ...

    def interpret_analytics(
        self, analytics: dict[str, Any]
    ) -> tuple[SalesInsightsResult, ExecutionInfo]: ...
