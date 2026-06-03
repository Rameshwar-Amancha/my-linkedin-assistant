"""
logging.py — Request logging middleware

Adds a unique request_id to each request and logs method, path, status, latency.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.monotonic()
        response: Response = await call_next(request)
        latency_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "[%s] %s %s → %d (%dms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
