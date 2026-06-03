"""
growth_service.py — Follower growth optimizer service.

Provides:
- Hashtag optimization for a given topic
- Optimal posting time recommendations (evidence-based, no external API needed)
- Personalized follower growth tips
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.factory import get_llm_provider
from app.models.schemas import (
    GrowthTip,
    GrowthTipsResponse,
    HashtagOptimizeResponse,
    HashtagSuggestion,
    OptimalTimingResponse,
)
from app.prompts.growth_prompts import growth_tips_prompt, hashtag_optimize_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optimal posting time data (research-backed, 2024-2026)
# Scores are relative engagement multipliers per slot.
# ---------------------------------------------------------------------------

POSTING_HEATMAP: dict[str, list[int]] = {
    "monday":    [7, 8, 12, 17],
    "tuesday":   [7, 8, 9, 12, 17, 18],
    "wednesday": [7, 8, 9, 12, 17, 18],
    "thursday":  [7, 8, 9, 12, 17, 18],
    "friday":    [7, 8, 12, 17],
    "saturday":  [9, 10],
    "sunday":    [10],
}

BEST_DAYS = ["Tuesday", "Wednesday", "Thursday"]
BEST_HOURS = [7, 8, 9, 12, 17, 18]


async def get_optimal_posting_times() -> OptimalTimingResponse:
    """Return evidence-based optimal posting times for LinkedIn (no LLM needed)."""
    return OptimalTimingResponse(
        best_days=BEST_DAYS,
        best_hours=BEST_HOURS,
        timezone_note=(
            "Times are in your local timezone. LinkedIn shows content during business hours "
            "in the viewer's timezone — post during YOUR 7-9am to catch your network as they "
            "start their day, and 5-7pm as they wind down. Mid-week (Tue-Thu) sees 30-50% "
            "more engagement than weekends for professional content."
        ),
        heatmap=POSTING_HEATMAP,
        reasoning=(
            "Based on LinkedIn algorithm research 2024-2026: early morning (7-9am) posts "
            "ride commute scroll time. Lunch hour (12pm) catches mid-day breaks. "
            "Early evening (5-7pm) catches end-of-workday browsing. "
            "Tuesday-Thursday are peak B2B days — avoid Monday (inbox overload) "
            "and Friday afternoon (checked-out mentally). Weekends have low engagement "
            "except for motivational/personal content."
        ),
    )


async def optimize_hashtags(
    topic: str,
    persona: str,
    target_audience: str,
) -> tuple[HashtagOptimizeResponse, int]:
    """Use LLM to suggest optimal hashtags for a topic."""
    provider = get_llm_provider()
    request = hashtag_optimize_prompt(topic, persona, target_audience)

    try:
        response = await provider.generate(request)
    except Exception as exc:
        logger.exception("LLM error in optimize_hashtags: %s", exc)
        raise

    raw = response.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse hashtag JSON, returning defaults")
        data = {
            "primary_hashtags": [],
            "secondary_hashtags": [],
            "avoid_hashtags": [],
            "recommended_count": 5,
        }

    def _parse_hashtags(items: list) -> list[HashtagSuggestion]:
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(HashtagSuggestion(
                    hashtag=str(item.get("hashtag", "")),
                    estimated_reach=str(item.get("estimated_reach", "medium")),
                    engagement_level=str(item.get("engagement_level", "medium")),
                    reason=str(item.get("reason", "")),
                ))
        return result

    return (
        HashtagOptimizeResponse(
            primary_hashtags=_parse_hashtags(data.get("primary_hashtags", [])),
            secondary_hashtags=_parse_hashtags(data.get("secondary_hashtags", [])),
            avoid_hashtags=[str(h) for h in data.get("avoid_hashtags", [])],
            recommended_count=int(data.get("recommended_count", 5)),
            tokens_used=response.total_tokens,
        ),
        response.total_tokens,
    )


async def get_growth_tips(
    style_description: str = "",
    post_count: int = 0,
) -> tuple[GrowthTipsResponse, int]:
    """Use LLM to generate personalized follower growth tips."""
    provider = get_llm_provider()
    request = growth_tips_prompt(style_description, post_count)

    try:
        response = await provider.generate(request)
    except Exception as exc:
        logger.exception("LLM error in get_growth_tips: %s", exc)
        raise

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse growth tips JSON")
        data = {"tips": [], "weekly_focus": "", "follower_growth_levers": []}

    tips = []
    for item in data.get("tips", []):
        if isinstance(item, dict):
            tips.append(GrowthTip(
                category=str(item.get("category", "content")),
                tip=str(item.get("tip", "")),
                impact=str(item.get("impact", "medium")),
                action=str(item.get("action", "")),
            ))

    return (
        GrowthTipsResponse(
            tips=tips,
            weekly_focus=str(data.get("weekly_focus", "")),
            follower_growth_levers=[str(l) for l in data.get("follower_growth_levers", [])],
        ),
        response.total_tokens,
    )
