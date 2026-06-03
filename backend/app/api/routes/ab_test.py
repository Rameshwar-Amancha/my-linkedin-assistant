"""
ab_test.py — A/B testing routes for post variation tracking
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import (
    ABTestRecordRequest,
    ABTestSummaryResponse,
    ABTestUpdateActualsRequest,
    ErrorResponse,
)
from app.services.ab_test_service import ABTestService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ab-testing"])


@router.post(
    "/ab-test/record",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Record which post variation a user selected",
    description=(
        "Tracks which variation index was chosen from a generate-post response. "
        "Use the topic_hash (hash of the topic string) to group results."
    ),
)
async def record_ab_selection(
    request: Request,
    payload: ABTestRecordRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = ABTestService(db)
    record = await service.record_selection(payload)
    return {
        "id": record.id,
        "style": record.style,
        "tone": record.tone,
        "persona": record.persona,
        "variation_index": record.variation_index,
        "engagement_prediction": record.engagement_prediction,
        "recorded": True,
    }


@router.patch(
    "/ab-test/record/{record_id}/actuals",
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Update A/B test record with actual engagement numbers",
    description="After a post is published, record actual reactions and comments to measure prediction accuracy.",
)
async def update_ab_actuals(
    record_id: str,
    payload: ABTestUpdateActualsRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    payload.record_id = record_id
    service = ABTestService(db)
    record = await service.update_actuals(payload)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A/B test record not found.")
    return {
        "id": record.id,
        "actual_reactions": record.actual_reactions,
        "actual_comments": record.actual_comments,
        "updated": True,
    }


@router.get(
    "/ab-test/summary",
    response_model=ABTestSummaryResponse,
    responses={401: {"model": ErrorResponse}},
    summary="Get A/B testing analytics summary",
    description="Returns aggregated stats on which styles, tones, and personas perform best.",
)
async def get_ab_summary(
    request: Request,
    limit: int = 200,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> ABTestSummaryResponse:
    service = ABTestService(db)
    return await service.get_summary(limit=min(limit, 1000))
