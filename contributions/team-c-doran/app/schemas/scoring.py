"""Schemas for lead scoring input and score card output."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LeadScoreResult(BaseModel):
    """Validated values returned by the lead scoring service."""

    lead_score: int = Field(ge=0, le=100)
    conversion_probability: float = Field(ge=0.0, le=1.0)
    priority_level: Literal["high", "medium", "low"]
    scoring_factors: dict[str, object]


class LeadScoreResponse(LeadScoreResult):
    """Persisted score card returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    score_id: int
    lead_id: int
