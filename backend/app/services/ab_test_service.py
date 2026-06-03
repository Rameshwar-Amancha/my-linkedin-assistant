"""
ab_test_service.py — A/B testing for post variations

Tracks which post variations users actually choose and
provides aggregate analytics on which styles/tones perform best.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ABTestRecord
from app.models.schemas import (
    ABTestRecordRequest,
    ABTestSummaryItem,
    ABTestSummaryResponse,
    ABTestUpdateActualsRequest,
)

logger = logging.getLogger(__name__)


class ABTestService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record_selection(self, request: ABTestRecordRequest) -> ABTestRecord:
        """Record that a user selected a particular post variation."""
        record = ABTestRecord(
            topic_hash=request.topic_hash,
            style=request.style,
            tone=request.tone,
            persona=request.persona,
            variation_index=request.variation_index,
            engagement_prediction=request.engagement_prediction,
        )
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(record)

        logger.info(
            "AB test recorded | style=%s tone=%s variation=%d prediction=%d",
            request.style,
            request.tone,
            request.variation_index,
            request.engagement_prediction,
        )
        return record

    async def update_actuals(self, request: ABTestUpdateActualsRequest) -> ABTestRecord | None:
        """Update a previously recorded selection with actual engagement numbers."""
        result = await self._db.execute(
            select(ABTestRecord).where(ABTestRecord.id == request.record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        record.actual_reactions = request.actual_reactions
        record.actual_comments = request.actual_comments
        await self._db.commit()
        await self._db.refresh(record)
        return record

    async def get_summary(self, limit: int = 100) -> ABTestSummaryResponse:
        """Aggregate A/B test results grouped by style + tone."""
        result = await self._db.execute(
            select(ABTestRecord).order_by(ABTestRecord.recorded_at.desc()).limit(limit)
        )
        records = result.scalars().all()

        if not records:
            return ABTestSummaryResponse(records_analyzed=0, summary=[])

        # Group by style+tone
        groups: dict[tuple[str, str, str], list[ABTestRecord]] = defaultdict(list)
        for r in records:
            groups[(r.style, r.tone, r.persona)].append(r)

        summary_items: list[ABTestSummaryItem] = []
        for (style, tone, persona), group in sorted(groups.items(), key=lambda x: -len(x[1])):
            avg_pred = sum(r.engagement_prediction for r in group) / len(group)
            avg_react = sum(r.actual_reactions for r in group) / len(group)
            avg_comm = sum(r.actual_comments for r in group) / len(group)
            summary_items.append(ABTestSummaryItem(
                style=style,
                tone=tone,
                persona=persona,
                total_uses=len(group),
                avg_predicted_score=round(avg_pred, 2),
                avg_actual_reactions=round(avg_react, 2),
                avg_actual_comments=round(avg_comm, 2),
            ))

        # Determine overall top style and tone by usage
        top_style = max(
            {s for s, _, _ in groups},
            key=lambda s: sum(len(v) for k, v in groups.items() if k[0] == s),
            default="",
        )
        top_tone = max(
            {t for _, t, _ in groups},
            key=lambda t: sum(len(v) for k, v in groups.items() if k[1] == t),
            default="",
        )

        return ABTestSummaryResponse(
            records_analyzed=len(records),
            top_style=top_style,
            top_tone=top_tone,
            summary=summary_items,
        )
