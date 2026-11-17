"""Request and response schemas for AI generated outreach campaigns."""

from pydantic import BaseModel, ConfigDict, Field


class OutreachRequest(BaseModel):
    """Options for generating a lead outreach email."""

    lead_id: int = Field(gt=0)
    tone: str = Field(default="professional", min_length=1, max_length=80)
    focus_points: str | None = None


class OutreachResponse(BaseModel):
    """Persisted outreach campaign returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    lead_id: int
    email_subject: str
    email_content: str
    follow_up_strategy: str
