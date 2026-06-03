"""
post.py — POST /api/generate-post route handler
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import ErrorResponse, GeneratePostRequest, GeneratePostResponse
from app.services.post_service import PostService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["content"])


@router.post(
    "/generate-post",
    response_model=GeneratePostResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate LinkedIn post variations",
    description=(
        "Generates one or more LinkedIn post variations for a given topic. "
        "Posts are returned as drafts — they are NEVER auto-published. "
        "The user must manually copy, edit, and post to LinkedIn."
    ),
)
async def generate_post(
    request: Request,
    payload: GeneratePostRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> GeneratePostResponse:
    logger.info(
        "[%s] generate-post | style=%s tone=%s variations=%d",
        request_id,
        payload.style,
        payload.tone,
        payload.variations,
    )

    service = PostService(db=db)
    try:
        result = await service.generate_post(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error("[%s] generate-post service error: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable. Please try again.",
        )
