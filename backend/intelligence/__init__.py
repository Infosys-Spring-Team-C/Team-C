"""Engine selection for the intelligence layer.

The product path is the reviewed AI package (``ai.*`` / ``utils.*``), originally
contributed by Mahidhar (``team-c-mahi``) and integrated here through a typed
adapter.  ``SALES_GENIE_AI_BACKEND=auto`` (the default) therefore selects the AI
package whenever it is importable.  The deterministic heuristic engine remains
available as an explicit, offline fallback.

Provider selection is also automatic by default: a configured OpenAI or Gemini
key is used when present, otherwise the AI package's deterministic **mock**
provider runs.  ``used_mock`` is always reported so the UI can label demo output
honestly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.config import Settings, get_settings
from backend.intelligence.contract import IntelligenceEngine, IntelligenceError

__all__ = [
    "IntelligenceEngine",
    "IntelligenceError",
    "get_engine",
    "reset_engine_cache",
    "describe_engine",
    "external_package_available",
]


def external_package_available() -> bool:
    """Return ``True`` when the reviewed AI package can be imported.

    Import failures are not cached: a deployment can install the package and
    restart without changing code.
    """
    try:
        import ai.graph  # noqa: F401
        import ai.providers  # noqa: F401
        import utils.config  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def get_engine() -> IntelligenceEngine:
    """Return the configured engine.

    ``auto`` (default) uses the AI package when present, else the heuristic.
    ``external`` requires the AI package and fails loudly if it is missing;
    ``heuristic`` forces the offline fallback.  A missing package is never
    silently replaced by a *different* engine when ``external`` is explicit.
    """
    settings: Settings = get_settings()
    backend = (settings.ai_backend or "auto").lower()

    if backend == "auto":
        backend = "external" if external_package_available() else "heuristic"

    if backend == "heuristic":
        from backend.intelligence.heuristic import HeuristicEngine

        return HeuristicEngine(settings)
    if backend == "external":
        from backend.intelligence.external import ExternalAIEngine

        return ExternalAIEngine(settings)
    raise IntelligenceError(
        f"Unsupported SALES_GENIE_AI_BACKEND={backend!r}. Use 'auto', 'external' or 'heuristic'."
    )


def describe_engine() -> dict[str, Any]:
    """Return non-secret engine metadata for the health endpoint and the UI.

    ``used_mock`` distinguishes a real model call from the deterministic demo
    provider.  ``real_ai`` is only true when an actual provider is configured.
    """
    settings = get_settings()
    try:
        engine = get_engine()
    except IntelligenceError as exc:
        return {
            "ai_backend": settings.ai_backend,
            "ai_provider": settings.ai_provider,
            "ai_model": settings.ai_model or "",
            "ai_used_mock": False,
            "ai_mode": "unavailable",
            "ai_note": "",
            "ai_status": f"unavailable: {exc}",
        }

    provider = str(getattr(engine, "provider", settings.ai_provider))
    model = str(getattr(engine, "model", settings.ai_model or ""))
    used_mock = bool(getattr(engine, "used_mock", provider == "mock"))
    return {
        "ai_backend": engine.name,
        "ai_provider": provider,
        "ai_model": model,
        "ai_used_mock": used_mock,
        "ai_mode": "live-model" if not used_mock else "offline-mock",
        "ai_note": str(getattr(engine, "note", "") or ""),
        "ai_status": "ok",
    }


def reset_engine_cache() -> None:
    get_engine.cache_clear()
