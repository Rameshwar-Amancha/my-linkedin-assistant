"""
algorithm_service.py — LinkedIn algorithm scoring service.

Analyzes a post and predicts its algorithm distribution potential,
provides actionable improvement suggestions, and recommends a
first-comment strategy to maximize early engagement velocity.
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.factory import get_llm_provider
from app.models.schemas import AlgorithmScoreResponse
from app.prompts.algorithm_prompts import algorithm_score_prompt
from app.utils.text_utils import extract_hashtags, word_count

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timing score lookup (no LLM needed)
# ---------------------------------------------------------------------------

_PEAK_HOURS = {7, 8, 9, 12, 17, 18}
_GOOD_HOURS = {6, 10, 11, 13, 16, 19}
_PEAK_DAYS = {"tuesday", "wednesday", "thursday"}
_GOOD_DAYS = {"monday", "friday"}


def _score_timing(hour: int | None, day: str | None) -> int:
    if hour is None and day is None:
        return 5  # neutral — user hasn't specified

    hour_score = 5
    if hour is not None:
        if hour in _PEAK_HOURS:
            hour_score = 9
        elif hour in _GOOD_HOURS:
            hour_score = 7
        else:
            hour_score = 3

    day_score = 5
    if day:
        day_lower = day.lower()
        if day_lower in _PEAK_DAYS:
            day_score = 9
        elif day_lower in _GOOD_DAYS:
            day_score = 6
        elif day_lower in {"saturday", "sunday"}:
            day_score = 3

    return round((hour_score + day_score) / 2)


async def score_post_for_algorithm(
    content: str,
    has_media: bool,
    scheduled_hour: int | None,
    scheduled_day: str | None,
) -> tuple[AlgorithmScoreResponse, int]:
    """Score a post for LinkedIn algorithm distribution potential."""
    wc = word_count(content)
    hashtags = extract_hashtags(content)
    hashtag_count = len(hashtags)
    timing_score = _score_timing(scheduled_hour, scheduled_day)

    provider = get_llm_provider()
    request = algorithm_score_prompt(
        content=content,
        word_count=wc,
        hashtag_count=hashtag_count,
        has_media=has_media,
        scheduled_hour=scheduled_hour,
        scheduled_day=scheduled_day,
    )

    try:
        response = await provider.generate(request)
    except Exception as exc:
        logger.exception("LLM error in score_post_for_algorithm: %s", exc)
        raise

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse algorithm score JSON, using defaults")
        data = {
            "algorithm_score": 5,
            "distribution_tier": "local",
            "hook_score": 5,
            "virality_score": 5,
            "timing_score": timing_score,
            "suggestions": ["Ensure strong hook in first line", "Use 3-5 hashtags"],
            "first_comment_tip": "Add a thoughtful question or key insight as your first comment immediately after posting.",
        }

    # Use locally-computed timing score if LLM didn't override it meaningfully
    llm_timing = int(data.get("timing_score", timing_score))
    final_timing = llm_timing if scheduled_hour is not None or scheduled_day is not None else timing_score

    return (
        AlgorithmScoreResponse(
            algorithm_score=min(10, max(0, int(data.get("algorithm_score", 5)))),
            distribution_tier=str(data.get("distribution_tier", "local")),
            hook_score=min(10, max(0, int(data.get("hook_score", 5)))),
            virality_score=min(10, max(0, int(data.get("virality_score", 5)))),
            word_count=wc,
            hashtag_count=hashtag_count,
            timing_score=min(10, max(0, final_timing)),
            suggestions=[str(s) for s in data.get("suggestions", [])],
            first_comment_tip=str(data.get("first_comment_tip", "")),
            tokens_used=response.total_tokens,
        ),
        response.total_tokens,
    )
