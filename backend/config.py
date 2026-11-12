"""Runtime configuration for the SalesGenie AI backend.

All values are read from environment variables (optionally loaded from a local
``.env`` file).  Nothing secret is ever hard-coded, and there are no default
credentials.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

try:  # python-dotenv is optional at runtime (Docker injects real env vars).
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - exercised only when the package is absent
    pass


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number, got {raw!r}") from exc


def _csv_list(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = "SalesGenie AI API"
    version: str = "1.0.0"
    environment: str = "development"

    database_url: str = "sqlite:///./salesgenie.db"
    cors_origins: tuple[str, ...] = ("http://localhost:8501", "http://127.0.0.1:8501")

    # --- Authentication -------------------------------------------------
    auth_enabled: bool = True
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120

    # --- AI / intelligence layer ---------------------------------------
    # "external"  = adapter around the reviewed AI package (ai.*) contributed
    #               by Mahidhar (team-c-mahi). This is the product path and the
    #               default; the package is included in this repository.
    # "auto"      = AI package when importable, deterministic heuristic otherwise.
    # "heuristic" = deterministic offline engine, kept as an explicit fallback.
    ai_backend: str = "external"
    # "auto" = Groq when GROQ_API_KEY is set, else OpenAI when OPENAI_API_KEY
    # is set, else Gemini when GOOGLE_API_KEY is set, else the package's
    # deterministic mock provider. "heuristic" keeps the offline engine as an
    # explicit, selectable fallback rather than the default.
    ai_provider: str = "auto"  # auto | mock | groq | gemini | openai
    ai_model: str = ""
    ai_temperature: float = 0.2
    ai_timeout_seconds: float = 20.0
    ai_max_transcript_chars: int = 42000
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    google_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""

    # --- Limits ---------------------------------------------------------
    max_csv_bytes: int = 5_000_000
    max_csv_rows: int = 5000
    default_page_size: int = 50
    max_page_size: int = 500

    score_threshold_qualified: int = 70
    score_threshold_nurture: int = 45

    def __post_init__(self) -> None:
        if self.auth_enabled and not self.jwt_secret:
            raise RuntimeError(
                "AUTH_ENABLED is true but JWT_SECRET is not set. "
                "Set JWT_SECRET to a long random value (see .env.example) or set "
                "AUTH_ENABLED=false for local development only."
            )
        if len(self.jwt_secret) and len(self.jwt_secret) < 16:
            raise RuntimeError("JWT_SECRET must be at least 16 characters long.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        environment=_str("SALES_GENIE_ENV", "development"),
        database_url=_str("DATABASE_URL", "sqlite:///./salesgenie.db"),
        cors_origins=_csv_list(
            "CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
        ),
        auth_enabled=_bool("AUTH_ENABLED", True),
        jwt_secret=_str("JWT_SECRET"),
        jwt_algorithm=_str("JWT_ALGORITHM", "HS256"),
        access_token_minutes=_int("ACCESS_TOKEN_MINUTES", 120),
        ai_backend=_str("SALES_GENIE_AI_BACKEND", "external").lower(),
        ai_provider=_str("SALES_GENIE_LLM_PROVIDER", "auto").lower(),
        ai_model=_str("SALES_GENIE_LLM_MODEL"),
        ai_temperature=_float("SALES_GENIE_LLM_TEMPERATURE", 0.2),
        ai_timeout_seconds=_float("SALES_GENIE_AI_TIMEOUT_SECONDS", 20.0),
        ai_max_transcript_chars=_int("SALES_GENIE_MAX_TRANSCRIPT_CHARS", 42000),
        groq_api_key=_str("GROQ_API_KEY") or _str("GROK_API_KEY"),
        groq_base_url=_str("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        google_api_key=_str("GOOGLE_API_KEY"),
        openai_api_key=_str("OPENAI_API_KEY"),
        openai_base_url=_str("OPENAI_BASE_URL"),
        max_csv_bytes=_int("MAX_CSV_BYTES", 5_000_000),
        max_csv_rows=_int("MAX_CSV_ROWS", 5000),
        default_page_size=_int("DEFAULT_PAGE_SIZE", 50),
        max_page_size=_int("MAX_PAGE_SIZE", 500),
        score_threshold_qualified=_int("SALES_GENIE_SCORE_THRESHOLD_QUALIFIED", 70),
        score_threshold_nurture=_int("SALES_GENIE_SCORE_THRESHOLD_NURTURE", 45),
    )


def reset_settings_cache() -> None:
    """Test helper: drop the cached settings so env changes take effect."""
    get_settings.cache_clear()
