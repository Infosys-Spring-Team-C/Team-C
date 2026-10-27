from __future__ import annotations
from typing import TypedDict, Any
from .schemas import ResearchResult, QualificationAssessment

class WorkflowState(TypedDict, total=False):
    operation: str
    request: dict[str, Any]
    research: ResearchResult
    qualification: QualificationAssessment
    result: Any
    errors: list[str]
    trace: list[str]
    started_at: float
