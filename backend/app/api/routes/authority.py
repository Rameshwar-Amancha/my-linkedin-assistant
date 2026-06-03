"""
authority.py — Authority and thought leadership analysis routes.

Endpoints:
  POST /api/authority/analyze       — Compute authority score from post samples
  GET  /api/authority/suggestions   — Get strategic engagement suggestions
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_request_id, verify_api_key
from app.models.schemas import (
    AuthorityAnalyzeRequest,
    AuthorityAnalyzeResponse,
    EngagementSuggestionsResponse,
)
from app.services import authority_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["authority"], dependencies=[Depends(verify_api_key)])


@router.post("/authority/analyze", response_model=AuthorityAnalyzeResponse)
async def analyze_authority(
    payload: AuthorityAnalyzeRequest,
    request_id: str = Depends(get_request_id),
) -> AuthorityAnalyzeResponse:
    """
    Analyze a set of your LinkedIn posts to compute an authority score,
    identify topic expertise areas, detect credibility signals,
    and generate growth actions.

    Submit 3-15 of your recent LinkedIn posts for best results.
    """
    result, tokens = await authority_service.analyze_authority(
        post_samples=payload.post_samples,
        professional_context=payload.professional_context,
    )
    logger.info(
        "[%s] Authority analysis: score=%d, topics=%s, tokens=%d",
        request_id, result.authority_score, result.topic_expertise, tokens,
    )
    return result


@router.get("/authority/suggestions", response_model=EngagementSuggestionsResponse)
async def get_engagement_suggestions(
    topics: str = Query(default="", description="Comma-separated topic expertise areas"),
    authority_score: int = Query(default=5, ge=0, le=10),
    request_id: str = Depends(get_request_id),
) -> EngagementSuggestionsResponse:
    """
    Get strategic engagement suggestions: what to comment on, posting cadence,
    comment templates, and authority-building content types.

    Pass your topic expertise areas (from /authority/analyze) for personalized advice.
    """
    topic_list = [t.strip() for t in topics.split(",") if t.strip()] if topics else []

    result, tokens = await authority_service.get_engagement_suggestions(
        topic_expertise=topic_list,
        authority_score=authority_score,
    )
    logger.info("[%s] Engagement suggestions generated, tokens=%d", request_id, tokens)
    return result
