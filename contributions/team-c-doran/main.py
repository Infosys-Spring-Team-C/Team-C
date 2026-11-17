"""FastAPI application entry point for SalesGenie AI."""

import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from app.api.crm import router as crm_router
from app.api.analytics import router as analytics_router
from app.api.leads import router as leads_router
from app.api.outreach import router as outreach_router
from app.api.scoring import router as scoring_router

app = FastAPI(title="SalesGenie AI API", version="1.0.0")
logger = logging.getLogger("salesgenie.http")
app.include_router(leads_router)
app.include_router(crm_router)
app.include_router(analytics_router)
app.include_router(outreach_router)
app.include_router(scoring_router)

# Streamlit is normally served from :8501. The regex also permits other local
# development ports without opening cross-origin access to remote hosts.
app.add_middleware(
    GZipMiddleware,
    minimum_size=500,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Measure request handling time, emit a header, and log the request."""
    started_at = perf_counter()
    response = await call_next(request)
    elapsed_seconds = perf_counter() - started_at
    response.headers["X-Process-Time"] = f"{elapsed_seconds:.6f}"
    logger.info(
        "%s %s completed with %s in %.3f ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_seconds * 1000,
    )
    return response


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a lightweight liveness response."""
    return {"status": "healthy", "service": "SalesGenie API"}


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Report database failures without exposing connection details."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is temporarily unavailable."},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return FastAPI request validation details in a stable envelope."""
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors raised outside request parsing."""
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
