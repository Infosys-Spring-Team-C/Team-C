"""Extensible scoring interfaces; no fitted model is shipped with the frontend layer."""
from __future__ import annotations
from typing import Any, Callable, Protocol
import numpy as np
from ai.schemas import LeadScoreResult, ScoreFactor
from .rule_based import calculate_lead_score


class LeadScorer(Protocol):
    def score(self, lead: dict[str, Any]) -> LeadScoreResult: ...


class RuleBasedLeadScorer:
    def __init__(self, weights: dict[str, float] | None = None, qualified_threshold: int = 70, nurture_threshold: int = 45):
        self.weights=weights; self.qualified_threshold=qualified_threshold; self.nurture_threshold=nurture_threshold
    def score(self, lead: dict[str, Any]) -> LeadScoreResult:
        return calculate_lead_score(lead,self.weights,self.qualified_threshold,self.nurture_threshold)


class EvaluatedSklearnLeadScorer:
    """Adapter for an externally trained/evaluated sklearn estimator.

    The trained artefact, feature definitions, labels, calibration report, and storage all belong
    to the approved model/backend layer. This adapter deliberately rejects use without an
    evaluation note so the UI cannot imply statistical accuracy for an unvalidated estimator.
    """
    def __init__(self, estimator: Any, feature_builder: Callable[[dict[str, Any]], list[float]], evaluation_note: str):
        if not evaluation_note.strip():
            raise ValueError("An evaluation note is required before enabling a trained lead-scoring model.")
        if not hasattr(estimator, "predict_proba"):
            raise TypeError("The estimator must expose predict_proba for this adapter.")
        self.estimator=estimator;self.feature_builder=feature_builder;self.evaluation_note=evaluation_note
    def score(self, lead: dict[str, Any]) -> LeadScoreResult:
        vector=np.asarray([self.feature_builder(lead)],dtype=float)
        probability=float(self.estimator.predict_proba(vector)[0][-1])
        score=max(0,min(100,round(probability*100)))
        category="Qualified" if score>=70 else ("Nurture" if score>=45 else "Low priority")
        return LeadScoreResult(score=score,qualification_category=category,
            factors=[ScoreFactor(name="Model output",weight=100,normalized_value=probability,points=score,
                                 explanation="Model score; inspect the backend model card for features and validation.",signal="neutral")],
            recommended_next_action="Review model factors and validate against current account context before acting.",
            methodology_note=f"Model-derived score. {self.evaluation_note} It must not be treated as a guaranteed conversion outcome.")
