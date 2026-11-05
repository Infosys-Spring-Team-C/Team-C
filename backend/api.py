"""FastAPI application factory.

Run locally with::

    uvicorn main:app --reload

OpenAPI documentation is served at ``/docs`` and ``/openapi.json``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.config import get_settings
from backend.db import SessionLocal, engine, get_db
from backend.errors import ApiError, api_error_handler, validation_error_handler
from backend.intelligence import describe_engine
from backend.routers import (
    analytics,
    auth,
    conversations,
    intelligence,
    leads,
    outreach,
    scoring,
)

__all__ = ["app", "create_app", "get_db"]

_DESCRIPTION = """
SalesGenie AI backend - AI sales assistant and lead intelligence platform.

* **Authentication**: OAuth2 password flow (`/api/v1/auth/token`). Send
  `Authorization: Bearer <token>` on every other endpoint.
* **Errors**: `{"detail": str, "code": str, "meta": object|null}`.
* **Pagination**: list endpoints return a JSON array and expose
  `X-Total-Count`, `X-Page` and `X-Page-Size` response headers.
* **AI**: company analysis, outreach, conversation summaries, scoring and
  recommendations run through `backend.intelligence`. The default
  `SALES_GENIE_AI_BACKEND=auto` uses the AI package (`ai.*`) and selects OpenAI
  or Gemini when a key is configured, otherwise its deterministic mock
  provider. The health endpoint reports `ai_provider`, `ai_model` and
  `ai_used_mock` so demo output is never misrepresented as a live model.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Total-Count", "X-Page", "X-Page-Size"],
    )

    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    for module in (auth, leads, intelligence, outreach, scoring, conversations, analytics):
        application.include_router(module.router)

    @application.get("/api/v1/health", tags=["system"])
    def health() -> dict:
        database = "ok"
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - depends on deployment
            database = f"unavailable: {exc.__class__.__name__}"

        try:
            engine_info = describe_engine()
        except Exception as exc:  # pragma: no cover - defensive
            engine_info = {
                "ai_backend": settings.ai_backend,
                "ai_provider": settings.ai_provider,
                "ai_model": settings.ai_model or "",
                "ai_used_mock": False,
                "ai_mode": "unavailable",
                "ai_note": "",
                "ai_status": f"unavailable: {exc.__class__.__name__}",
            }

        return {
            "status": "ok" if database == "ok" else "degraded",
            "version": settings.version,
            "database": database,
            "database_dialect": engine.dialect.name,
            "auth_enabled": settings.auth_enabled,
            **engine_info,
        }

    @application.get("/health", include_in_schema=False)
    def health_alias() -> dict:
        return health()

    @application.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return application


app = create_app()
