"""
calendar_service.py — Content calendar / scheduled posts management

Provides CRUD operations for scheduling LinkedIn post drafts.
Posts are NEVER auto-published — users must manually post them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ScheduledPost
from app.models.schemas import (
    CalendarResponse,
    ScheduledPostCreate,
    ScheduledPostResponse,
    ScheduledPostUpdate,
)

logger = logging.getLogger(__name__)


def _to_response(post: ScheduledPost) -> ScheduledPostResponse:
    return ScheduledPostResponse(
        id=post.id,
        title=post.title,
        content=post.content,
        scheduled_for=post.scheduled_for.isoformat() if post.scheduled_for else "",
        status=post.status,
        style=post.style,
        tone=post.tone,
        persona=post.persona,
        hashtags=post.hashtags or [],
        notes=post.notes or "",
        created_at=post.created_at.isoformat() if post.created_at else "",
        updated_at=post.updated_at.isoformat() if post.updated_at else "",
    )


class CalendarService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_post(self, request: ScheduledPostCreate) -> ScheduledPostResponse:
        """Schedule a new post draft."""
        scheduled_for = datetime.fromisoformat(request.scheduled_for.replace("Z", "+00:00"))

        post = ScheduledPost(
            title=request.title,
            content=request.content,
            scheduled_for=scheduled_for,
            status="scheduled",
            style=request.style,
            tone=request.tone,
            persona=request.persona,
            hashtags=request.hashtags,
            notes=request.notes,
        )
        self._db.add(post)
        await self._db.commit()
        await self._db.refresh(post)

        logger.info("Calendar post created | id=%s scheduled_for=%s", post.id, scheduled_for.isoformat())
        return _to_response(post)

    async def get_posts(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> CalendarResponse:
        """List scheduled posts, optionally filtered by status."""
        query = select(ScheduledPost).order_by(ScheduledPost.scheduled_for.asc())
        if status:
            query = query.where(ScheduledPost.status == status)
        query = query.limit(limit)

        result = await self._db.execute(query)
        posts = result.scalars().all()

        return CalendarResponse(
            posts=[_to_response(p) for p in posts],
            total=len(posts),
        )

    async def get_post(self, post_id: str) -> ScheduledPostResponse | None:
        """Fetch a single scheduled post."""
        result = await self._db.execute(
            select(ScheduledPost).where(ScheduledPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        return _to_response(post) if post else None

    async def update_post(
        self, post_id: str, update: ScheduledPostUpdate
    ) -> ScheduledPostResponse | None:
        """Partially update a scheduled post."""
        result = await self._db.execute(
            select(ScheduledPost).where(ScheduledPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return None

        if update.title is not None:
            post.title = update.title
        if update.content is not None:
            post.content = update.content
        if update.scheduled_for is not None:
            post.scheduled_for = datetime.fromisoformat(update.scheduled_for.replace("Z", "+00:00"))
        if update.status is not None:
            valid_statuses = {"draft", "scheduled", "published", "cancelled"}
            if update.status not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
            post.status = update.status
        if update.hashtags is not None:
            post.hashtags = update.hashtags
        if update.notes is not None:
            post.notes = update.notes

        post.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(post)

        logger.info("Calendar post updated | id=%s status=%s", post.id, post.status)
        return _to_response(post)

    async def delete_post(self, post_id: str) -> bool:
        """Delete a scheduled post. Returns True if deleted."""
        result = await self._db.execute(
            select(ScheduledPost).where(ScheduledPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return False

        await self._db.delete(post)
        await self._db.commit()
        logger.info("Calendar post deleted | id=%s", post_id)
        return True
