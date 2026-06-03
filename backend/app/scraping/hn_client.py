"""
hn_client.py — Hacker News Algolia API client

Uses only the official HN Algolia public API — no scraping.
Fetches stories posted in the last 48 hours (search_by_date) so results
reflect what is trending *right now*, not just all-time popular stories.
Rate limited to avoid excessive requests.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx

from app.models.schemas import TrendItem

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hn.algolia.com/api/v1"
REQUEST_TIMEOUT = 10.0
RATE_LIMIT_DELAY = 0.5  # seconds between requests
TRENDING_WINDOW_HOURS = 48  # only consider stories this fresh
MIN_POINTS = 15  # lower bar than all-time search since fresh stories haven't had time to accumulate


class HackerNewsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def fetch_top_stories(self, limit: int = 20) -> list[TrendItem]:
        """
        Fetch recently trending stories from HN via Algolia's date-sorted endpoint.
        Uses created_at_i filter to restrict to the last TRENDING_WINDOW_HOURS so
        returned topics are genuinely current, not evergreen popular stories.
        """
        cutoff = int(time.time()) - TRENDING_WINDOW_HOURS * 3600
        try:
            response = await self._client.get(
                f"{HN_API_BASE}/search_by_date",
                params={
                    "tags": "story",
                    "hitsPerPage": min(limit * 2, 60),
                    "numericFilters": f"created_at_i>{cutoff},points>{MIN_POINTS}",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("HN API request failed: %s", e)
            return []

        await asyncio.sleep(RATE_LIMIT_DELAY)

        try:
            data = response.json()
        except ValueError:
            logger.warning("HN API returned invalid JSON.")
            return []

        now_ts = time.time()
        items: list[TrendItem] = []
        for hit in data.get("hits", [])[:limit]:
            title = hit.get("title", "").strip()
            if not title:
                continue

            points = hit.get("points") or 0
            num_comments = hit.get("num_comments") or 0
            created_at_i = hit.get("created_at_i") or int(now_ts)

            engagement = _score_engagement(points, num_comments)
            recency = _score_recency(now_ts - created_at_i)
            published_dt = datetime.fromtimestamp(created_at_i, tz=timezone.utc).isoformat()

            items.append(TrendItem(
                topic=title,
                source="hackernews",
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                engagement_potential=engagement,
                recency_score=recency,
                suggested_angle=_generate_angle(title),
                published_at=published_dt,
            ))

        return items

    async def close(self) -> None:
        await self._client.aclose()


def _score_engagement(points: int, comments: int) -> int:
    """Score engagement potential 1-10 based on HN points and comment count."""
    raw = (points * 0.5) + (comments * 1.5)
    if raw > 2000:
        return 10
    elif raw > 1000:
        return 9
    elif raw > 500:
        return 8
    elif raw > 200:
        return 7
    elif raw > 100:
        return 6
    elif raw > 50:
        return 5
    elif raw > 20:
        return 4
    else:
        return 3


def _score_recency(age_seconds: float) -> int:
    """Score freshness 1-10; stories under 3 hours old score highest."""
    age_hours = age_seconds / 3600
    if age_hours < 1:
        return 10
    elif age_hours < 3:
        return 9
    elif age_hours < 6:
        return 8
    elif age_hours < 12:
        return 7
    elif age_hours < 24:
        return 6
    elif age_hours < 36:
        return 4
    else:
        return 2


def _generate_angle(title: str) -> str:
    """Generate a LinkedIn-specific angle suggestion from an HN story title."""
    title_lower = title.lower()

    if any(kw in title_lower for kw in ["survey", "study", "report", "%", "data shows", "statistics"]):
        return "Share the most counterintuitive finding — add your reaction and what your team sees in practice"
    elif any(kw in title_lower for kw in ["why ", "how ", "the truth", "the real reason"]):
        return "Agree, disagree, or extend with a concrete example from your own experience"
    elif any(kw in title_lower for kw in ["launch", "release", "introducing", "announcing", "ships"]):
        return "Analyze what gap this fills and whether it changes your team's workflow today"
    elif any(kw in title_lower for kw in ["fail", "mistake", "wrong", "broken", "problem"]):
        return "Turn this into a '1 lesson I wish I'd known earlier' post with personal context"
    elif any(kw in title_lower for kw in ["ai", "gpt", "llm", "ml", "claude", "gemini", "agent", "copilot"]):
        return "Share one concrete workflow change you're making because of this — concrete beats theoretical"
    elif any(kw in title_lower for kw in ["layoff", "hiring", "job", "career", "fired", "restructur"]):
        return "Give your honest take — what this signals for tech careers and what to do about it"
    elif any(kw in title_lower for kw in ["open source", "github", "repo"]):
        return "Explain why engineers should care and link to a use case from your work"
    elif any(kw in title_lower for kw in ["startup", "founder", "vc", "funding", "raised"]):
        return "Share the business lesson buried in this story — what would you have done differently?"
    else:
        return "Add your professional perspective — what's the implication for your industry?"
