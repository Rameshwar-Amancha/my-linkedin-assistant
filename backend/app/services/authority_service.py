"""
authority_service.py — LinkedIn authority and thought leadership analysis service.

Analyzes post samples to compute an authority score, identify topic expertise,
and generate strategic engagement recommendations.
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.factory import get_llm_provider
from app.models.schemas import (
    AuthorityAnalyzeResponse,
    CredibilitySignals,
    EngagementSuggestionsResponse,
)
from app.prompts.algorithm_prompts import authority_analyze_prompt, engagement_suggestions_prompt

logger = logging.getLogger(__name__)


async def analyze_authority(
    post_samples: list[str],
    professional_context: str,
) -> tuple[AuthorityAnalyzeResponse, int]:
    """Analyze post samples and compute authority score + growth actions."""
    # Combine samples with clear separators (cap at 6000 chars total to stay in token budget)
    combined = "\n\n---\n\n".join(post_samples)
    if len(combined) > 6000:
        combined = combined[:6000] + "\n[...truncated for analysis]"

    provider = get_llm_provider()
    request = authority_analyze_prompt(combined, professional_context)

    try:
        response = await provider.generate(request)
    except Exception as exc:
        logger.exception("LLM error in analyze_authority: %s", exc)
        raise

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse authority JSON, using defaults")
        data = {
            "authority_score": 5,
            "topic_expertise": [],
            "engagement_tips": [],
            "credibility_signals": {},
            "authority_summary": "Unable to parse analysis results.",
            "growth_actions": [],
        }

    signals_raw = data.get("credibility_signals", {})
    credibility = CredibilitySignals(
        uses_data_stats=bool(signals_raw.get("uses_data_stats", False)),
        uses_personal_stories=bool(signals_raw.get("uses_personal_stories", False)),
        uses_specific_examples=bool(signals_raw.get("uses_specific_examples", False)),
        uses_frameworks=bool(signals_raw.get("uses_frameworks", False)),
        has_contrarian_views=bool(signals_raw.get("has_contrarian_views", False)),
        mentions_credentials=bool(signals_raw.get("mentions_credentials", False)),
    )

    return (
        AuthorityAnalyzeResponse(
            authority_score=min(10, max(0, int(data.get("authority_score", 5)))),
            topic_expertise=[str(t) for t in data.get("topic_expertise", [])],
            engagement_tips=[str(t) for t in data.get("engagement_tips", [])],
            credibility_signals=credibility,
            authority_summary=str(data.get("authority_summary", "")),
            growth_actions=[str(a) for a in data.get("growth_actions", [])],
            tokens_used=response.total_tokens,
        ),
        response.total_tokens,
    )


async def get_engagement_suggestions(
    topic_expertise: list[str],
    authority_score: int,
) -> tuple[EngagementSuggestionsResponse, int]:
    """Generate strategic engagement suggestions based on expertise areas."""
    provider = get_llm_provider()
    request = engagement_suggestions_prompt(topic_expertise, authority_score)

    try:
        response = await provider.generate(request)
    except Exception as exc:
        logger.exception("LLM error in get_engagement_suggestions: %s", exc)
        raise

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse engagement suggestions JSON")
        data = {
            "topics_to_comment_on": [],
            "posting_cadence": "3x per week",
            "engagement_strategy": "",
            "comment_templates": [],
            "authority_building_content": [],
        }

    return (
        EngagementSuggestionsResponse(
            topics_to_comment_on=[str(t) for t in data.get("topics_to_comment_on", [])],
            posting_cadence=str(data.get("posting_cadence", "3x per week")),
            engagement_strategy=str(data.get("engagement_strategy", "")),
            comment_templates=[str(t) for t in data.get("comment_templates", [])],
            authority_building_content=[str(c) for c in data.get("authority_building_content", [])],
        ),
        response.total_tokens,
    )
