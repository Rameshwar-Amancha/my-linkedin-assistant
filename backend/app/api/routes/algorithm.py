"""
algorithm.py — LinkedIn algorithm scoring route.

Endpoints:
  POST /api/algorithm/score   — Score a post for LinkedIn algorithm distribution
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.dependencies import get_request_id, verify_api_key
from app.models.schemas import AlgorithmScoreRequest, AlgorithmScoreResponse
from app.services import algorithm_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["algorithm"], dependencies=[Depends(verify_api_key)])


@router.post("/algorithm/score", response_model=AlgorithmScoreResponse)
async def score_post(
    payload: AlgorithmScoreRequest,
    request_id: str = Depends(get_request_id),
) -> AlgorithmScoreResponse:
    """
    Score a LinkedIn post for algorithm distribution potential.

    Returns:
    - algorithm_score (0-10): overall likelihood of broad distribution
    - distribution_tier: local | broad | viral
    - hook_score: first-line effectiveness
    - virality_score: shareability / save-worthiness
    - timing_score: quality of the planned posting time
    - suggestions: 3-5 specific improvements
    - first_comment_tip: what to post as your first comment to boost early engagement
    """
    result, tokens = await algorithm_service.score_post_for_algorithm(
        content=payload.content,
        has_media=payload.has_media,
        scheduled_hour=payload.scheduled_hour,
        scheduled_day=payload.scheduled_day,
    )
    logger.info(
        "[%s] Algorithm score: %d (%s), tokens=%d",
        request_id, result.algorithm_score, result.distribution_tier, tokens,
    )
    return result
