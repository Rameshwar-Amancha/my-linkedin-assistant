"""
analysis_service.py — Business logic for post quality analysis
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.base import LLMProviderError, LLMRequest
from app.llm.factory import get_llm_provider
from app.models.schemas import AnalyzePostRequest, AnalyzePostResponse, PostScores
from app.prompts.analysis_prompts import build_analysis_prompt

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self) -> None:
        self._llm = get_llm_provider()

    async def analyze(self, request: AnalyzePostRequest) -> AnalyzePostResponse:
        """
        Analyze a LinkedIn post for quality, hook strength, and engagement potential.
        """
        system_prompt, user_prompt = build_analysis_prompt(request)

        llm_request = LLMRequest(
            messages=self._llm.build_messages(system_prompt, user_prompt),
            max_tokens=1000,
            temperature=0.3,  # Low temperature for consistent scoring
        )

        try:
            response = await self._llm.generate_with_timing(llm_request)
        except LLMProviderError as e:
            logger.error("LLM error in post analysis: %s", e)
            raise RuntimeError(str(e)) from e

        if not response.success:
            raise RuntimeError("LLM returned empty response.")

        parsed = _parse_analysis_response(response.content)

        logger.info(
            "Post analyzed | tokens=%d latency=%dms overall=%d",
            response.total_tokens,
            response.latency_ms,
            parsed["scores"]["overall"],
        )

        return AnalyzePostResponse(
            scores=PostScores(**parsed["scores"]),
            recommendations=parsed["recommendations"],
            summary=parsed.get("summary", ""),
            tokens_used=response.total_tokens,
        )


def _parse_analysis_response(content: str) -> dict:
    """Parse structured analysis JSON from LLM."""
    json_match = re.search(r"```json\s*([\s\S]+?)\s*```", content)
    raw = json_match.group(1) if json_match else content.strip()

    try:
        data = json.loads(raw)
        scores = data.get("scores", {})
        return {
            "scores": {
                "hook_strength": _clamp(int(scores.get("hook_strength", 5)), 0, 10),
                "readability": _clamp(int(scores.get("readability", 5)), 0, 10),
                "authority_signals": _clamp(int(scores.get("authority_signals", 5)), 0, 10),
                "emotional_triggers": _clamp(int(scores.get("emotional_triggers", 5)), 0, 10),
                "cta_effectiveness": _clamp(int(scores.get("cta_effectiveness", 5)), 0, 10),
                "overall": _clamp(int(scores.get("overall", 5)), 0, 10),
            },
            "recommendations": [str(r) for r in data.get("recommendations", [])[:8]],
            "summary": str(data.get("summary", "")).strip(),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Could not parse analysis JSON — using defaults.")
        return {
            "scores": {
                "hook_strength": 5,
                "readability": 5,
                "authority_signals": 5,
                "emotional_triggers": 5,
                "cta_effectiveness": 5,
                "overall": 5,
            },
            "recommendations": ["Could not parse detailed recommendations."],
            "summary": content.strip()[:500],
        }


def _clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
