"""
webhook_service.py — Outbound webhook notification system

Manages webhook subscriptions and fires HMAC-signed HTTP POST
notifications to registered endpoints when events occur.

Security:
- Each webhook payload is HMAC-SHA256 signed with the subscription secret
- Subscriptions store their signing secrets in plaintext (needed for signing)
- Webhook URLs are validated as HTTP/HTTPS only
- Failed webhooks are tracked; after 10 consecutive failures the subscription
  is automatically deactivated
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.orm import WebhookSubscription
from app.models.schemas import WebhookCreate, WebhookListResponse, WebhookResponse

logger = logging.getLogger(__name__)

settings = get_settings()

MAX_CONSECUTIVE_FAILURES = 10
WEBHOOK_TIMEOUT_SECONDS = 10.0


def _to_response(sub: WebhookSubscription) -> WebhookResponse:
    return WebhookResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events or [],
        description=sub.description or "",
        is_active=sub.is_active,
        failure_count=sub.failure_count,
        last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
        created_at=sub.created_at.isoformat() if sub.created_at else "",
    )


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_subscription(self, request: WebhookCreate) -> WebhookResponse:
        """Register a new webhook endpoint."""
        signing_secret = (
            request.secret
            or settings.WEBHOOK_SIGNING_SECRET
            or secrets.token_hex(32)
        )

        sub = WebhookSubscription(
            url=request.url,
            events=request.events,
            secret=signing_secret,
            description=request.description,
            is_active=True,
        )
        self._db.add(sub)
        await self._db.commit()
        await self._db.refresh(sub)

        logger.info("Webhook registered | id=%s url=%s events=%s", sub.id, sub.url, sub.events)
        return _to_response(sub)

    async def list_subscriptions(self) -> WebhookListResponse:
        result = await self._db.execute(
            select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
        )
        subs = result.scalars().all()
        return WebhookListResponse(webhooks=[_to_response(s) for s in subs], total=len(subs))

    async def delete_subscription(self, webhook_id: str) -> bool:
        result = await self._db.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return False
        await self._db.delete(sub)
        await self._db.commit()
        logger.info("Webhook deleted | id=%s", webhook_id)
        return True

    async def toggle_active(self, webhook_id: str, is_active: bool) -> WebhookResponse | None:
        result = await self._db.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
        sub.is_active = is_active
        if is_active:
            sub.failure_count = 0  # reset on re-enable
        await self._db.commit()
        await self._db.refresh(sub)
        return _to_response(sub)

    # ------------------------------------------------------------------
    # Firing
    # ------------------------------------------------------------------

    async def fire_event(self, event: str, payload: dict) -> None:
        """
        Send webhook notifications to all active subscribers for the given event.
        Failures are logged and tracked; silently swallowed so they don't break callers.
        """
        result = await self._db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.is_active == True,  # noqa: E712
            )
        )
        subs = result.scalars().all()

        matching = [s for s in subs if event in (s.events or [])]
        if not matching:
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        full_payload = {"event": event, "fired_at": now_iso, "data": payload}

        for sub in matching:
            await self._deliver(sub, full_payload)

    async def _deliver(self, sub: WebhookSubscription, payload: dict) -> None:
        """Deliver payload to a single webhook subscription."""
        body = json.dumps(payload, default=str)
        signature = _sign_payload(body, sub.secret)

        headers = {
            "Content-Type": "application/json",
            "X-LEA-Signature": f"sha256={signature}",
            "X-LEA-Event": payload.get("event", ""),
        }

        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(sub.url, content=body, headers=headers)
            response.raise_for_status()

            sub.failure_count = 0
            sub.last_triggered_at = datetime.now(timezone.utc)
            logger.info("Webhook delivered | id=%s url=%s event=%s", sub.id, sub.url, payload.get("event"))

        except Exception as e:
            sub.failure_count += 1
            logger.warning(
                "Webhook delivery failed | id=%s url=%s failures=%d error=%s",
                sub.id, sub.url, sub.failure_count, e,
            )
            if sub.failure_count >= MAX_CONSECUTIVE_FAILURES:
                sub.is_active = False
                logger.warning("Webhook deactivated after %d failures | id=%s", MAX_CONSECUTIVE_FAILURES, sub.id)

        await self._db.commit()


def _sign_payload(body: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
