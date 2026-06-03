"""
export_service.py — Export engagement history and drafts to CSV

Provides async CSV generation for:
- Saved drafts history
- Engagement metrics history
- A/B test records
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import ABTestRecord, EngagementMetric, SavedDraft

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def export_drafts_csv(self, limit: int = 500) -> str:
        """Export saved drafts as CSV string."""
        result = await self._db.execute(
            select(SavedDraft).order_by(SavedDraft.created_at.desc()).limit(limit)
        )
        drafts = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(["id", "label", "draft_type", "tone", "engagement_score", "content", "created_at"])

        for draft in drafts:
            writer.writerow([
                draft.id,
                draft.label,
                draft.draft_type,
                draft.tone,
                draft.engagement_score,
                draft.content.replace("\n", "\\n"),  # flatten newlines for CSV
                draft.created_at.isoformat() if draft.created_at else "",
            ])

        logger.info("Exported %d drafts to CSV", len(drafts))
        return output.getvalue()

    async def export_engagement_csv(self, limit: int = 500) -> str:
        """Export engagement metrics as CSV string."""
        result = await self._db.execute(
            select(EngagementMetric).order_by(EngagementMetric.recorded_at.desc()).limit(limit)
        )
        metrics = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "id", "post_url_hash", "predicted_score",
            "actual_reactions", "actual_comments", "draft_id", "recorded_at",
        ])

        for metric in metrics:
            writer.writerow([
                metric.id,
                metric.post_url_hash,
                metric.predicted_score,
                metric.actual_reactions,
                metric.actual_comments,
                metric.draft_id or "",
                metric.recorded_at.isoformat() if metric.recorded_at else "",
            ])

        logger.info("Exported %d engagement metrics to CSV", len(metrics))
        return output.getvalue()

    async def export_ab_tests_csv(self, limit: int = 500) -> str:
        """Export A/B test records as CSV string."""
        result = await self._db.execute(
            select(ABTestRecord).order_by(ABTestRecord.recorded_at.desc()).limit(limit)
        )
        records = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "id", "topic_hash", "style", "tone", "persona",
            "variation_index", "engagement_prediction",
            "actual_reactions", "actual_comments", "recorded_at",
        ])

        for r in records:
            writer.writerow([
                r.id,
                r.topic_hash,
                r.style,
                r.tone,
                r.persona,
                r.variation_index,
                r.engagement_prediction,
                r.actual_reactions,
                r.actual_comments,
                r.recorded_at.isoformat() if r.recorded_at else "",
            ])

        logger.info("Exported %d A/B test records to CSV", len(records))
        return output.getvalue()

    @staticmethod
    def _now_filename_tag() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
