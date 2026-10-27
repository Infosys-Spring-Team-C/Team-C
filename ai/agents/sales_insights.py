from __future__ import annotations
from typing import Any
from ai.schemas import SalesInsightsResult, SalesInsight
from ai.providers import BaseLLMProvider
from ._base import structured_task

def interpret_sales_analytics(analytics: dict[str, Any], provider: BaseLLMProvider) -> SalesInsightsResult:
    def mock() -> SalesInsightsResult:
        insights=[]
        pipeline=analytics.get("pipeline_distribution", [])
        if pipeline:
            largest=max(pipeline, key=lambda x: x.get("count", 0))
            insights.append(SalesInsight(title="Largest pipeline segment", observation=f"{largest.get('stage', 'Unknown')} contains {largest.get('count', 0)} leads.", evidence="Backend-supplied pipeline distribution.", confidence="high"))
        activity=analytics.get("activity_trend", [])
        if len(activity) >= 2:
            first,last=activity[0],activity[-1]
            insights.append(SalesInsight(title="Activity movement", observation=f"Activity changed from {first.get('activity', 0)} to {last.get('activity', 0)} across the displayed period.", evidence="Backend-supplied activity trend.", confidence="medium"))
        if not insights: insights.append(SalesInsight(title="Insufficient analytics", observation="No aggregate measures were supplied for trend analysis.", evidence="Empty backend analytics response.", confidence="low"))
        return SalesInsightsResult(insights=insights, caveat="Observations describe supplied aggregates only; they do not establish causes or forecast results.")
    return structured_task(provider, "sales_insights", {"analytics": analytics}, SalesInsightsResult, mock)
