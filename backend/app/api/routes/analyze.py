"""
analyze.py — POST /api/analyze-post route handler
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_request_id, verify_api_key
from app.models.schemas import AnalyzePostRequest, AnalyzePostResponse, ErrorResponse
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze-post",
    response_model=AnalyzePostResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Analyze a LinkedIn post for quality and engagement potential",
    description=(
        "Analyzes a LinkedIn post across multiple dimensions: "
        "hook strength, readability, authority signals, emotional triggers, "
        "and CTA effectiveness. Returns actionable improvement recommendations."
    ),
)
async def analyze_post(
    request: Request,
    payload: AnalyzePostRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
) -> AnalyzePostResponse:
    logger.info(
        "[%s] analyze-post | mode=%s content_len=%d",
        request_id,
        payload.mode,
        len(payload.content),
    )

    service = AnalysisService()
    try:
        result = await service.analyze(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error("[%s] analyze-post service error: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable. Please try again.",
        )
