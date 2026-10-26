"""Engine selection for the intelligence layer."""
from __future__ import annotations

from functools import lru_cache

from backend.config import Settings, get_settings
from backend.intelligence.contract import IntelligenceEngine, IntelligenceError

__all__ = [
    "IntelligenceEngine",
    "IntelligenceError",
    "get_engine",
    "reset_engine_cache",
]


@lru_cache(maxsize=1)
def get_engine() -> IntelligenceEngine:
    """Return the configured engine.

    ``heuristic`` (default) needs no credentials.  ``external`` requires the
    reviewed AI package to be present; a missing package is reported as a
    configuration error instead of silently degrading to a different engine.
    """
    settings: Settings = get_settings()
    backend = settings.ai_backend
    if backend == "heuristic":
        from backend.intelligence.heuristic import HeuristicEngine

        return HeuristicEngine(settings)
    if backend == "external":
        from backend.intelligence.external import ExternalAIEngine

        return ExternalAIEngine(settings)
    raise IntelligenceError(
        f"Unsupported SALES_GENIE_AI_BACKEND={backend!r}. Use 'heuristic' or 'external'."
    )


def reset_engine_cache() -> None:
    get_engine.cache_clear()
