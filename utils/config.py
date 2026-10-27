"""Runtime configuration. Secrets are read only from environment / Streamlit secrets."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
import json
import os
from typing import Any


def _secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    try:
        import streamlit as st
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def _boolean(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _endpoint_overrides(value: str) -> dict[str, str]:
    """Read an optional JSON path map without failing app startup for a bad setting."""
    if not value.strip():
        return {}
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict) or not all(isinstance(k, str) and isinstance(v, str) and v.startswith("/") for k, v in parsed.items()):
            raise ValueError
        return parsed
    except (json.JSONDecodeError, ValueError):
        return {}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    backend_base_url: str = ""
    backend_api_prefix: str = "/api/v1"
    backend_token: str = ""
    # Optional JSON map, for example {"follow_ups":"/tasks/follow-ups"}; path contracts stay configurable.
    backend_endpoint_overrides: dict[str, str] = field(default_factory=dict)
    request_timeout_seconds: float = 15.0
    request_retries: int = 2
    llm_provider: str = "mock"  # mock | openai | gemini
    llm_model: str = "deterministic-demo-v1"
    openai_api_key: str = ""
    google_api_key: str = ""
    llm_temperature: float = 0.2
    max_transcript_chars: int = 42000
    score_threshold_qualified: int = 70
    score_threshold_nurture: int = 45


def get_settings(overrides: dict[str, Any] | None = None) -> Settings:
    settings = Settings(
        demo_mode=_boolean(_secret("SALES_GENIE_DEMO_MODE", "true"), True),
        backend_base_url=_secret("SALES_GENIE_BACKEND_BASE_URL").rstrip("/"),
        backend_api_prefix=_secret("SALES_GENIE_BACKEND_API_PREFIX", "/api/v1"),
        backend_token=_secret("SALES_GENIE_BACKEND_TOKEN"),
        backend_endpoint_overrides=_endpoint_overrides(_secret("SALES_GENIE_ENDPOINT_OVERRIDES_JSON")),
        request_timeout_seconds=float(_secret("SALES_GENIE_REQUEST_TIMEOUT_SECONDS", "15")),
        request_retries=int(_secret("SALES_GENIE_REQUEST_RETRIES", "2")),
        llm_provider=_secret("SALES_GENIE_LLM_PROVIDER", "mock").lower(),
        llm_model=_secret("SALES_GENIE_LLM_MODEL", "deterministic-demo-v1"),
        openai_api_key=_secret("OPENAI_API_KEY"),
        google_api_key=_secret("GOOGLE_API_KEY"),
        llm_temperature=float(_secret("SALES_GENIE_LLM_TEMPERATURE", "0.2")),
        max_transcript_chars=int(_secret("SALES_GENIE_MAX_TRANSCRIPT_CHARS", "42000")),
        score_threshold_qualified=int(_secret("SALES_GENIE_SCORE_THRESHOLD_QUALIFIED", "70")),
        score_threshold_nurture=int(_secret("SALES_GENIE_SCORE_THRESHOLD_NURTURE", "45")),
    )
    return replace(settings, **(overrides or {}))


def runtime_settings() -> Settings:
    """Merge non-secret, per-browser configuration chosen in the UI."""
    base = get_settings()
    try:
        import streamlit as st
        allowed = st.session_state.get("salesgenie_runtime_config", {})
        safe = {k: v for k, v in allowed.items() if k in {
            "demo_mode", "backend_base_url", "llm_provider", "llm_model",
            "llm_temperature", "request_timeout_seconds", "score_threshold_qualified",
            "score_threshold_nurture",
        }}
        return replace(base, **safe)
    except Exception:
        return base
