"""
calendar.py — Content calendar CRUD routes

Schedule LinkedIn post drafts for future publishing.
Posts are NEVER auto-published — this is a planning tool only.
Users must manually post to LinkedIn at the scheduled time.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import (
    CalendarResponse,
    ErrorResponse,
    ScheduledPostCreate,
    ScheduledPostResponse,
    ScheduledPostUpdate,
)
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["calendar"])


@router.post(
    "/calendar",
    response_model=ScheduledPostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Schedule a LinkedIn post draft",
    description=(
        "Add a post draft to the content calendar. "
        "This does NOT auto-publish — it only stores the draft with a target date. "
        "You must manually post to LinkedIn at the scheduled time."
    ),
)
async def create_scheduled_post(
    request: Request,
    payload: ScheduledPostCreate,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> ScheduledPostResponse:
    service = CalendarService(db)
    try:
        return await service.create_post(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/calendar",
    response_model=CalendarResponse,
    responses={401: {"model": ErrorResponse}},
    summary="List scheduled posts",
)
async def list_scheduled_posts(
    request: Request,
    status_filter: str = Query(default="", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> CalendarResponse:
    service = CalendarService(db)
    return await service.get_posts(
        status=status_filter if status_filter else None,
        limit=limit,
    )


@router.get(
    "/calendar/{post_id}",
    response_model=ScheduledPostResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Get a single scheduled post",
)
async def get_scheduled_post(
    post_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> ScheduledPostResponse:
    service = CalendarService(db)
    post = await service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled post not found.")
    return post


@router.patch(
    "/calendar/{post_id}",
    response_model=ScheduledPostResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Update a scheduled post",
)
async def update_scheduled_post(
    post_id: str,
    request: Request,
    payload: ScheduledPostUpdate,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> ScheduledPostResponse:
    service = CalendarService(db)
    try:
        post = await service.update_post(post_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled post not found.")
    return post


@router.delete(
    "/calendar/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Delete a scheduled post",
)
async def delete_scheduled_post(
    post_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = CalendarService(db)
    deleted = await service.delete_post(post_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled post not found.")
