"""
reply_service.py — Business logic for draft reply generation
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.base import LLMRequest, LLMProviderError
from app.llm.factory import get_llm_provider
from app.models.schemas import DraftReplyRequest, DraftReplyResponse
from app.prompts.reply_prompts import build_reply_prompt

logger = logging.getLogger(__name__)


class ReplyService:
    def __init__(self, db=None) -> None:
        self._llm = get_llm_provider()
        self._db = db  # optional; used for style hints

    async def generate_reply(self, request: DraftReplyRequest) -> DraftReplyResponse:
        """
        Generate a thoughtful, authentic reply draft.

        Returns structured response with reply text, reasoning, and engagement score.
        Never submits anything to LinkedIn — only generates text.
        """
        # Fetch personal style hint if db session available
        style_hint = ""
        if self._db:
            try:
                from app.services.style_service import StyleService
                style_hint = await StyleService(self._db).get_style_hint()
            except Exception:
                pass

        system_prompt, user_prompt = build_reply_prompt(request, style_hint=style_hint)

        llm_request = LLMRequest(
            messages=self._llm.build_messages(system_prompt, user_prompt),
            max_tokens=800,
            temperature=_temperature_for_tone(request.tone),
        )

        try:
            response = await self._llm.generate_with_timing(llm_request)
        except LLMProviderError as e:
            logger.error("LLM error in reply generation: %s", e)
            raise RuntimeError(str(e)) from e

        if not response.success:
            raise RuntimeError("LLM returned empty response.")

        parsed = _parse_reply_response(response.content)

        logger.info(
            "Reply generated | tokens=%d latency=%dms score=%d",
            response.total_tokens,
            response.latency_ms,
            parsed["engagement_score"],
        )

        return DraftReplyResponse(
            reply=parsed["reply"],
            reasoning=parsed["reasoning"],
            engagement_score=parsed["engagement_score"],
            tone_used=request.tone,
            tokens_used=response.total_tokens,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _temperature_for_tone(tone: str) -> float:
    """Adjust temperature based on tone for better outputs."""
    return {
        "professional": 0.6,
        "concise": 0.5,
        "expert": 0.65,
        "contrarian": 0.8,
        "founder": 0.75,
        "recruiter": 0.65,
        "thoughtful_question": 0.7,
    }.get(tone, 0.7)


def _parse_reply_response(content: str) -> dict:
    """
    Parse structured JSON response from LLM.
    Falls back to treating the entire content as the reply if parsing fails.
    """
    # Try JSON block extraction first
    json_match = re.search(r"```json\s*([\s\S]+?)\s*```", content)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            return {
                "reply": str(data.get("reply", "")).strip(),
                "reasoning": str(data.get("reasoning", "")).strip(),
                "engagement_score": _clamp(int(data.get("engagement_score", 5)), 0, 10),
            }
        except (json.JSONDecodeError, ValueError):
            pass

    # Try raw JSON
    try:
        data = json.loads(content.strip())
        return {
            "reply": str(data.get("reply", "")).strip(),
            "reasoning": str(data.get("reasoning", "")).strip(),
            "engagement_score": _clamp(int(data.get("engagement_score", 5)), 0, 10),
        }
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: treat full content as reply
    logger.warning("Could not parse structured LLM response — using raw content as reply.")
    return {
        "reply": content.strip(),
        "reasoning": "",
        "engagement_score": 5,
    }


def _clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
