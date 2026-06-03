"""
reply.py — POST /api/draft-reply route handler
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import DraftReplyRequest, DraftReplyResponse, ErrorResponse
from app.services.reply_service import ReplyService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["engagement"])


@router.post(
    "/draft-reply",
    response_model=DraftReplyResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate an AI-assisted reply draft",
    description=(
        "Generates a thoughtful reply draft for a LinkedIn post. "
        "The draft is returned to the user — it is NEVER auto-submitted. "
        "All LinkedIn posting actions require explicit user confirmation."
    ),
)
async def draft_reply(
    request: Request,
    payload: DraftReplyRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> DraftReplyResponse:
    logger.info(
        "[%s] draft-reply | tone=%s persona=%s content_len=%d",
        request_id,
        payload.tone,
        payload.persona,
        len(payload.post_content),
    )

    service = ReplyService(db=db)
    try:
        result = await service.generate_reply(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error("[%s] draft-reply service error: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable. Please try again.",
        )
