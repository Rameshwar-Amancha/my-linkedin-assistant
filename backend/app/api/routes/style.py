"""
style.py — Personal writing style model routes

Build and retrieve a writing style profile learned from the user's own drafts.
The profile is injected into future prompt generation to match the user's voice.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import ErrorResponse, StyleLearnRequest, StyleProfileResponse
from app.services.style_service import StyleService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["style"])


@router.post(
    "/style/learn",
    response_model=StyleProfileResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Learn writing style from draft samples",
    description=(
        "Analyzes provided draft samples (post or reply text) to extract a "
        "personal writing style fingerprint. Updates the default style profile. "
        "Provide at least 3 samples for best results."
    ),
)
async def learn_style(
    request: Request,
    payload: StyleLearnRequest,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> StyleProfileResponse:
    logger.info("[%s] style/learn | samples=%d", request_id, len(payload.draft_samples))
    service = StyleService(db)
    try:
        return await service.learn_from_drafts(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error("[%s] style/learn LLM error: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable. Please try again.",
        )


@router.get(
    "/style/profile",
    response_model=StyleProfileResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Get current writing style profile",
    description="Returns the currently active style profile. Use POST /style/learn to create or update it.",
)
async def get_style_profile(
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> StyleProfileResponse:
    service = StyleService(db)
    profile = await service.get_profile()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No style profile found. Use POST /api/style/learn to create one.",
        )
    return profile


@router.delete(
    "/style/profile",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Reset the writing style profile",
)
async def reset_style_profile(
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    from sqlalchemy import select, delete
    from app.models.orm import StyleProfile

    result = await db.execute(select(StyleProfile).where(StyleProfile.profile_name == "default"))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No style profile found.")

    await db.delete(profile)
    await db.commit()
    logger.info("[%s] Style profile reset.", request_id)
