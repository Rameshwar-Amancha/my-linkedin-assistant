"""
time_tracking.py — LinkedIn time tracking routes.

Endpoints:
  POST /api/time-tracking/log       — Extension reports session time (no auth for simplicity—
                                      uses the same X-API-Key as all other endpoints)
  GET  /api/time-tracking/summary   — 7-day rolling summary with insights
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import TimeSessionLog, TimeTrackingSummaryResponse
from app.services import time_tracking_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["time-tracking"], dependencies=[Depends(verify_api_key)])


@router.post("/time-tracking/log", status_code=204, response_class=Response)
async def log_session(
    payload: TimeSessionLog,
    db: AsyncSession = Depends(get_database),
    request_id: str = Depends(get_request_id),
) -> Response:
    """
    Log a LinkedIn usage session reported by the browser extension.
    Called periodically (e.g. every 5 minutes or on tab close) by the content script.
    Accumulates on existing records for the same date.
    """
    await time_tracking_service.log_session(db, payload)
    logger.info(
        "[%s] Session logged: date=%s active=%ds productive=%ds",
        request_id, payload.session_date, payload.active_seconds, payload.productive_seconds,
    )
    return Response(status_code=204)


@router.get("/time-tracking/summary", response_model=TimeTrackingSummaryResponse)
async def get_time_summary(
    db: AsyncSession = Depends(get_database),
    request_id: str = Depends(get_request_id),
) -> TimeTrackingSummaryResponse:
    """
    Return a 7-day rolling summary of LinkedIn time usage with insights.
    Useful for the extension's Growth dashboard to display time budget progress.
    """
    summary = await time_tracking_service.get_time_summary(db)
    logger.info(
        "[%s] Time summary: today=%dmin week=%dmin focus=%.0f%%",
        request_id, summary.today_active_minutes, summary.week_active_minutes,
        summary.focus_ratio * 100,
    )
    return summary
