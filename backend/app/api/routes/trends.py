"""
trends.py — GET /api/trends route handler
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import ErrorResponse, TrendsResponse
from app.services.trend_service import TrendService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["discovery"])


@router.get(
    "/trends",
    response_model=TrendsResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Fetch trending topics for LinkedIn engagement",
    description=(
        "Aggregates trending tech, business, and AI topics from public sources "
        "(Hacker News, RSS feeds, News API). Results are cached. "
        "Only public data from consenting platforms is used."
    ),
)
async def get_trends(
    request: Request,
    category: str = Query(default="", description="Filter by category: tech, business, ai, leadership, startups"),
    limit: int = Query(default=15, ge=1, le=50, description="Number of trends to return"),
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> TrendsResponse:
    logger.info("[%s] get-trends | category=%r limit=%d", request_id, category, limit)

    service = TrendService(db=db)
    return await service.get_trends(category=category, limit=limit)
