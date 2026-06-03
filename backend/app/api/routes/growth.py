"""
growth.py — Follower growth optimizer routes.

Endpoints:
  GET  /api/growth/optimal-times      — Best posting times (evidence-based)
  POST /api/growth/hashtag-optimize   — Optimal hashtags for a topic
  GET  /api/growth/tips               — Personalized follower growth tips
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.orm import StyleProfile
from app.models.schemas import (
    GrowthTipsResponse,
    HashtagOptimizeRequest,
    HashtagOptimizeResponse,
    OptimalTimingResponse,
)
from app.services import growth_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["growth"], dependencies=[Depends(verify_api_key)])


@router.get("/growth/optimal-times", response_model=OptimalTimingResponse)
async def get_optimal_times(
    request_id: str = Depends(get_request_id),
) -> OptimalTimingResponse:
    """
    Return evidence-based optimal posting times for LinkedIn.
    No LLM call — purely data-driven heatmap.
    """
    return await growth_service.get_optimal_posting_times()


@router.post("/growth/hashtag-optimize", response_model=HashtagOptimizeResponse)
async def hashtag_optimize(
    payload: HashtagOptimizeRequest,
    request_id: str = Depends(get_request_id),
) -> HashtagOptimizeResponse:
    """
    Suggest optimal hashtags for a LinkedIn post topic.
    Returns primary (3-5), secondary (5-8), and hashtags to avoid.
    """
    result, _ = await growth_service.optimize_hashtags(
        topic=payload.topic,
        persona=payload.persona,
        target_audience=payload.target_audience,
    )
    logger.info("[%s] Hashtag optimization for topic (len=%d)", request_id, len(payload.topic))
    return result


@router.get("/growth/tips", response_model=GrowthTipsResponse)
async def get_growth_tips(
    db: AsyncSession = Depends(get_database),
    request_id: str = Depends(get_request_id),
) -> GrowthTipsResponse:
    """
    Return personalized follower growth tips.
    Uses the user's saved style profile for personalization if available.
    """
    style_description = ""
    post_count = 0
    try:
        result = await db.execute(
            select(StyleProfile).where(StyleProfile.profile_name == "default")
        )
        profile = result.scalar_one_or_none()
        if profile:
            style_description = profile.style_description
            post_count = profile.sample_count
    except Exception:
        pass  # Gracefully degrade if style profile isn't available

    result_data, _ = await growth_service.get_growth_tips(
        style_description=style_description,
        post_count=post_count,
    )
    logger.info("[%s] Growth tips generated (%d tips)", request_id, len(result_data.tips))
    return result_data
