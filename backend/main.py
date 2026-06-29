"""
main.py — FastAPI application entry point

Configures:
- Application factory
- Middleware (CORS, logging, rate limiting)
- Route registration
- Database initialization
- Health endpoint
- Global exception handlers
"""

import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import reply, post, trends, analyze, ab_test, export, calendar, style, webhooks
from app.api.routes import growth, algorithm, authority, time_tracking
from app.config.settings import get_settings
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.database import init_db

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs once on startup and shutdown."""
    logger.info("Starting LinkedIn Engagement Assistant API v%s", settings.APP_VERSION)
    await init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down LinkedIn Engagement Assistant API.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_application() -> FastAPI:
    application = FastAPI(
        title="LinkedIn Engagement Assistant API",
        description=(
            "AI-assisted LinkedIn engagement platform. "
            "Generates reply drafts, posts, trends, and post analysis. "
            "All LinkedIn actions require explicit user confirmation."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS — restrict to configured origins only
    #
    # NOTE: Starlette's CORSMiddleware does NOT support wildcard patterns
    # inside allow_origins (e.g. "chrome-extension://*"). Instead we use
    # allow_origin_regex to match all chrome-extension://<any-id> origins,
    # and keep allow_origins for exact-match origins (localhost, etc.).
    # -----------------------------------------------------------------------
    exact_origins: list[str] = []
    chrome_extension_regex: str | None = None

    for origin in settings.ALLOWED_ORIGINS:
        origin_str = str(origin).strip()
        if not origin_str:
            continue
        if "chrome-extension://" in origin_str:
            # Match any Chrome extension origin via regex
            chrome_extension_regex = r"chrome-extension://[a-z]+"
        elif origin_str == "*":
            # Wildcard — allow all
            exact_origins.append("*")
        else:
            exact_origins.append(origin_str)

    # Build middleware kwargs
    cors_kwargs: dict[str, Any] = {
        "allow_credentials": False,  # No cookies used
        "allow_methods": ["GET", "POST", "PATCH", "DELETE"],
        "allow_headers": ["Content-Type", "X-API-Key", "X-Request-ID", "X-Extension-Version"],
    }

    if chrome_extension_regex:
        cors_kwargs["allow_origin_regex"] = chrome_extension_regex

    if exact_origins:
        cors_kwargs["allow_origins"] = exact_origins
    else:
        cors_kwargs["allow_origins"] = []  # at least empty list

    application.add_middleware(CORSMiddleware, **cors_kwargs)

    # -----------------------------------------------------------------------
    # Custom middleware
    # -----------------------------------------------------------------------
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(LoggingMiddleware)

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    application.include_router(reply.router, prefix="/api")
    application.include_router(post.router, prefix="/api")
    application.include_router(trends.router, prefix="/api")
    application.include_router(analyze.router, prefix="/api")
    application.include_router(ab_test.router, prefix="/api")
    application.include_router(export.router, prefix="/api")
    application.include_router(calendar.router, prefix="/api")
    application.include_router(style.router, prefix="/api")
    application.include_router(webhooks.router, prefix="/api")
    application.include_router(growth.router, prefix="/api")
    application.include_router(algorithm.router, prefix="/api")
    application.include_router(authority.router, prefix="/api")
    application.include_router(time_tracking.router, prefix="/api")

    # -----------------------------------------------------------------------
    # Health endpoint (no auth required)
    # -----------------------------------------------------------------------
    @application.get("/api/health", tags=["system"])
    async def health_check():
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "provider": settings.LLM_PROVIDER,
        }

    # -----------------------------------------------------------------------
    # Global exception handlers
    # -----------------------------------------------------------------------
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Unhandled exception [request_id=%s] %s: %s",
            request_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred. Please try again.",
                "request_id": request_id,
            },
        )

    return application


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )