"""
webhooks.py — Webhook subscription management routes

Register outbound webhooks to receive notifications when events
occur in the LinkedIn Engagement Assistant.

Supported events:
  trends_updated   — New trending topics fetched
  draft_saved      — A new draft was saved
  post_generated   — A post was generated
  reply_generated  — A reply draft was generated

Webhook payloads are HMAC-SHA256 signed via the X-LEA-Signature header.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database, get_request_id, verify_api_key
from app.models.schemas import (
    ErrorResponse,
    WebhookCreate,
    WebhookListResponse,
    WebhookResponse,
)
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Register a webhook subscription",
    description=(
        "Subscribe to LEA events. When an event fires, your endpoint will receive "
        "a signed HTTP POST. Verify the X-LEA-Signature header using your secret."
    ),
)
async def create_webhook(
    request: Request,
    payload: WebhookCreate,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> WebhookResponse:
    service = WebhookService(db)
    try:
        return await service.create_subscription(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/webhooks",
    response_model=WebhookListResponse,
    responses={401: {"model": ErrorResponse}},
    summary="List all webhook subscriptions",
)
async def list_webhooks(
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> WebhookListResponse:
    service = WebhookService(db)
    return await service.list_subscriptions()


@router.patch(
    "/webhooks/{webhook_id}/toggle",
    response_model=WebhookResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Enable or disable a webhook subscription",
)
async def toggle_webhook(
    webhook_id: str,
    request: Request,
    is_active: bool,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
) -> WebhookResponse:
    service = WebhookService(db)
    result = await service.toggle_active(webhook_id, is_active)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")
    return result


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
    summary="Delete a webhook subscription",
)
async def delete_webhook(
    webhook_id: str,
    request: Request,
    request_id: str = Depends(get_request_id),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_database),
):
    service = WebhookService(db)
    deleted = await service.delete_subscription(webhook_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")
