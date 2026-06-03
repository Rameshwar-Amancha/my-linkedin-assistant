"""
rate_limit.py — In-memory token bucket rate limiter middleware

Limits requests per IP address using a sliding window counter.
Returns 429 Too Many Requests with Retry-After header on excess.

This is intentionally simple. For production, use Redis-backed rate limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config.settings import get_settings

# Fallback defaults — overridden at construction from Settings
DEFAULT_REQUESTS_PER_MINUTE = 60
DEFAULT_BURST_SIZE = 10


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int | None = None,
        burst_size: int = DEFAULT_BURST_SIZE,
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        _settings = get_settings()
        self._rpm = requests_per_minute if requests_per_minute is not None else _settings.RATE_LIMIT_REQUESTS
        self._burst = burst_size
        self._exempt = set(exempt_paths or ["/api/health", "/docs", "/openapi.json"])
        # {ip: [timestamps]}
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._exempt:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.monotonic()
        window = self._windows[client_ip]

        # Evict timestamps older than 60 seconds
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.pop(0)

        if len(window) >= self._rpm:
            retry_after = int(60 - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For if behind a trusted proxy."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
