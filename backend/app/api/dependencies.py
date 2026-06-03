"""
dependencies.py — FastAPI dependency injection

Shared dependencies used across route handlers:
- API key authentication
- Database session
- LLM factory access
"""

import logging

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    """
    Validate the X-API-Key header against the configured secret.

    Uses constant-time comparison to prevent timing attacks.
    Returns 401 (not 422) when the header is absent.
    """
    import hmac

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to prevent timing side-channel attacks
    if not hmac.compare_digest(x_api_key, settings.API_SECRET_KEY):
        logger.warning("Invalid API key attempt from unknown client.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return x_api_key


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

async def get_database() -> AsyncSession:  # type: ignore[override]
    async for session in get_db():
        yield session


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------

async def get_request_id(request: Request) -> str:
    """Return the request ID set by LoggingMiddleware."""
    return getattr(request.state, "request_id", "unknown")
