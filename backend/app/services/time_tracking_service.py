"""
time_tracking_service.py — LinkedIn time tracking service.

Aggregates session time data reported by the extension and
returns weekly/daily summaries with productivity insights.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import TimeTrackingSession
from app.models.schemas import TimeSessionLog, TimeTrackingSummaryResponse

logger = logging.getLogger(__name__)


async def log_session(db: AsyncSession, payload: TimeSessionLog) -> None:
    """Upsert a time tracking session for a given date (aggregate per day)."""
    result = await db.execute(
        select(TimeTrackingSession).where(
            TimeTrackingSession.session_date == payload.session_date
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Accumulate on top of what's already stored for this date
        existing.active_seconds += payload.active_seconds
        existing.idle_seconds += payload.idle_seconds
        existing.page_views += payload.page_views
        existing.actions_taken += payload.actions_taken
        existing.productive_seconds += payload.productive_seconds
    else:
        session = TimeTrackingSession(
            session_date=payload.session_date,
            active_seconds=payload.active_seconds,
            idle_seconds=payload.idle_seconds,
            page_views=payload.page_views,
            actions_taken=payload.actions_taken,
            productive_seconds=payload.productive_seconds,
        )
        db.add(session)

    await db.commit()


async def get_time_summary(db: AsyncSession) -> TimeTrackingSummaryResponse:
    """Compute a 7-day rolling summary of LinkedIn time usage."""
    today = date.today()
    today_str = today.isoformat()
    week_ago_str = (today - timedelta(days=6)).isoformat()

    result = await db.execute(
        select(TimeTrackingSession).where(
            TimeTrackingSession.session_date >= week_ago_str
        ).order_by(TimeTrackingSession.session_date.desc())
    )
    sessions = result.scalars().all()

    today_active = 0
    today_productive = 0
    week_active = 0
    week_productive = 0
    daily_breakdown = []

    session_map = {s.session_date: s for s in sessions}

    # Build a full 7-day breakdown (fill zeros for days with no data)
    for i in range(6, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        s = session_map.get(day)
        active_min = round((s.active_seconds if s else 0) / 60)
        productive_min = round((s.productive_seconds if s else 0) / 60)
        daily_breakdown.append({
            "date": day,
            "active_minutes": active_min,
            "productive_minutes": productive_min,
            "page_views": s.page_views if s else 0,
            "actions_taken": s.actions_taken if s else 0,
        })
        week_active += active_min
        week_productive += productive_min
        if day == today_str:
            today_active = active_min
            today_productive = productive_min

    focus_ratio = round(week_productive / week_active, 2) if week_active > 0 else 0.0

    insights = _generate_insights(
        today_active, week_active, today_productive, week_productive, focus_ratio
    )

    return TimeTrackingSummaryResponse(
        today_active_minutes=today_active,
        today_productive_minutes=today_productive,
        week_active_minutes=week_active,
        week_productive_minutes=week_productive,
        daily_breakdown=daily_breakdown,
        insights=insights,
        focus_ratio=focus_ratio,
    )


def _generate_insights(
    today_active: int,
    week_active: int,
    today_productive: int,
    week_productive: int,
    focus_ratio: float,
) -> list[str]:
    insights = []

    if today_active > 60:
        insights.append(
            f"You've spent {today_active} min on LinkedIn today — consider a break. "
            "Quality engagement beats time-on-site."
        )
    elif today_active > 0:
        insights.append(
            f"Today: {today_active} min on LinkedIn. "
            f"{today_productive} min using AI tools productively."
        )

    avg_daily = round(week_active / 7)
    if avg_daily > 45:
        insights.append(
            f"Average {avg_daily} min/day this week. "
            "LinkedIn research shows 20-30 min of focused engagement beats 2+ hours of passive scrolling."
        )
    elif avg_daily > 0:
        insights.append(f"Average {avg_daily} min/day on LinkedIn this week.")

    if focus_ratio >= 0.5:
        insights.append(
            f"Great focus ratio ({int(focus_ratio * 100)}% of LinkedIn time is productive). "
            "You're using the platform intentionally."
        )
    elif focus_ratio > 0 and week_active > 0:
        insights.append(
            f"Focus ratio: {int(focus_ratio * 100)}% productive. "
            "Try opening LinkedIn with a specific goal (reply to 3 posts, write 1 post) to boost this."
        )

    if week_productive > 0:
        insights.append(
            f"This week: {week_productive} min spent on AI-assisted content creation — "
            "that's time building your brand."
        )

    return insights
