"""
post_service.py — Business logic for LinkedIn post generation
"""

from __future__ import annotations

import json
import logging
import re

from app.llm.base import LLMProviderError, LLMRequest
from app.llm.factory import get_llm_provider
from app.models.schemas import (
    GeneratePostRequest,
    GeneratePostResponse,
    PostVariation,
)
from app.prompts.post_prompts import build_post_prompt

logger = logging.getLogger(__name__)


class PostService:
    def __init__(self, db=None) -> None:
        self._llm = get_llm_provider()
        self._db = db  # optional; used for style hints

    async def generate_post(self, request: GeneratePostRequest) -> GeneratePostResponse:
        """
        Generate multiple LinkedIn post variations.

        Returns drafts only — NEVER auto-publishes.
        User must manually copy and post to LinkedIn.
        """
        # Fetch personal style hint if db session available
        style_hint = ""
        if self._db:
            try:
                from app.services.style_service import StyleService
                style_hint = await StyleService(self._db).get_style_hint()
            except Exception:
                pass  # Style hint is optional

        all_variations: list[PostVariation] = []
        total_tokens = 0

        batch_size = min(request.variations, 3)
        system_prompt, user_prompt = build_post_prompt(request, batch_size, style_hint=style_hint)

        llm_request = LLMRequest(
            messages=self._llm.build_messages(system_prompt, user_prompt),
            max_tokens=1500 * batch_size,
            temperature=_temperature_for_style(request.style),
        )

        try:
            response = await self._llm.generate_with_timing(llm_request)
        except LLMProviderError as e:
            logger.error("LLM error in post generation: %s", e)
            raise RuntimeError(str(e)) from e

        if not response.success:
            raise RuntimeError("LLM returned empty response.")

        total_tokens += response.total_tokens
        parsed_variations = _parse_post_response(response.content, batch_size)
        all_variations.extend(parsed_variations)

        # If more variations requested, generate in another batch
        if request.variations > 3:
            remaining = request.variations - 3
            system_prompt2, user_prompt2 = build_post_prompt(request, remaining, offset=3, style_hint=style_hint)
            llm_request2 = LLMRequest(
                messages=self._llm.build_messages(system_prompt2, user_prompt2),
                max_tokens=1500 * remaining,
                temperature=_temperature_for_style(request.style) + 0.1,
            )
            try:
                response2 = await self._llm.generate_with_timing(llm_request2)
                total_tokens += response2.total_tokens
                all_variations.extend(_parse_post_response(response2.content, remaining))
            except LLMProviderError:
                logger.warning("Second batch generation failed — returning first batch only.")

        logger.info(
            "Post generated | variations=%d tokens=%d style=%s",
            len(all_variations),
            total_tokens,
            request.style,
        )

        return GeneratePostResponse(
            variations=all_variations[:request.variations],
            topic_analyzed=request.topic[:200],
            tokens_used=total_tokens,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _temperature_for_style(style: str) -> float:
    return {
        "professional": 0.6,
        "educational": 0.65,
        "founder": 0.8,
        "technical": 0.6,
        "viral": 0.85,
        "concise_authority": 0.55,
    }.get(style, 0.7)


def _parse_post_response(content: str, expected_count: int) -> list[PostVariation]:
    """
    Parse structured JSON array of post variations from LLM output.
    Falls back to single-variation extraction if JSON parsing fails.
    """
    # Try JSON block
    json_match = re.search(r"```json\s*([\s\S]+?)\s*```", content)
    raw = json_match.group(1) if json_match else content.strip()

    try:
        data = json.loads(raw)
        items = data if isinstance(data, list) else data.get("variations", [data])
        return [
            PostVariation(
                content=str(item.get("content", "")).strip(),
                hashtags=list(item.get("hashtags", [])),
                engagement_prediction=_clamp(int(item.get("engagement_prediction", 5)), 0, 10),
                word_count=len(str(item.get("content", "")).split()),
            )
            for item in items[:expected_count]
            if item.get("content")
        ]
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Could not parse post JSON — using raw content.")

    # Fallback: split by separator pattern
    parts = re.split(r"---+|===+|\n{3,}", content.strip())
    variations = []
    for part in parts[:expected_count]:
        part = part.strip()
        if len(part) > 50:
            variations.append(PostVariation(
                content=part,
                hashtags=_extract_hashtags(part),
                engagement_prediction=5,
                word_count=len(part.split()),
            ))

    if not variations:
        variations.append(PostVariation(
            content=content.strip(),
            hashtags=_extract_hashtags(content),
            engagement_prediction=5,
            word_count=len(content.split()),
        ))

    return variations


def _extract_hashtags(text: str) -> list[str]:
    """Extract hashtags from post text."""
    return re.findall(r"#\w+", text)


def _clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
