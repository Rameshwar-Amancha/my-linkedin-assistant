"""
style_service.py — Personal writing style model

Analyzes a user's draft samples using LLM to extract a
writing style profile that can be injected into future prompts.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProviderError, LLMRequest
from app.llm.factory import get_llm_provider
from app.models.orm import StyleProfile
from app.models.schemas import StyleLearnRequest, StyleProfileResponse
from app.utils.text_utils import avg_sentence_length, word_count

logger = logging.getLogger(__name__)

_STYLE_ANALYSIS_SYSTEM = """You are a writing style analyst. Given a set of text samples from one author,
extract their writing style fingerprint.

OUTPUT FORMAT (JSON only, no extra text):
```json
{
  "sentence_length_pref": "short|medium|long",
  "vocabulary_level": "casual|professional|technical",
  "avg_post_length": 150,
  "preferred_styles": ["concise_authority", "educational"],
  "style_description": "2-3 sentence description of the author's distinctive voice and patterns."
}
```

sentence_length_pref: short (<10 words avg), medium (10-20), long (>20)
vocabulary_level: casual (conversational), professional (business-formal), technical (domain-specific jargon)
preferred_styles: from [professional, educational, founder, technical, viral, concise_authority]
style_description: be specific about patterns, not generic."""


class StyleService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._llm = get_llm_provider()

    async def learn_from_drafts(self, request: StyleLearnRequest) -> StyleProfileResponse:
        """
        Analyze draft samples and update (or create) the default style profile.
        """
        samples_text = "\n\n---\n\n".join(request.draft_samples[:10])  # cap at 10 samples

        user_prompt = f"Analyze these {len(request.draft_samples)} writing samples:\n\n{samples_text}"

        llm_request = LLMRequest(
            messages=self._llm.build_messages(_STYLE_ANALYSIS_SYSTEM, user_prompt),
            max_tokens=500,
            temperature=0.3,
        )

        try:
            response = await self._llm.generate_with_timing(llm_request)
        except LLMProviderError as e:
            logger.error("LLM error in style analysis: %s", e)
            raise RuntimeError(str(e)) from e

        parsed = _parse_style_response(response.content, request.draft_samples)

        # Upsert: update existing default profile or create a new one
        result = await self._db.execute(
            select(StyleProfile).where(StyleProfile.profile_name == "default")
        )
        profile = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if profile:
            profile.sentence_length_pref = parsed["sentence_length_pref"]
            profile.vocabulary_level = parsed["vocabulary_level"]
            profile.avg_post_length = parsed["avg_post_length"]
            profile.preferred_styles = parsed["preferred_styles"]
            profile.style_description = parsed["style_description"]
            profile.sample_count += len(request.draft_samples)
            profile.updated_at = now
        else:
            profile = StyleProfile(
                profile_name="default",
                sentence_length_pref=parsed["sentence_length_pref"],
                vocabulary_level=parsed["vocabulary_level"],
                avg_post_length=parsed["avg_post_length"],
                preferred_styles=parsed["preferred_styles"],
                style_description=parsed["style_description"],
                sample_count=len(request.draft_samples),
            )
            self._db.add(profile)

        await self._db.commit()
        await self._db.refresh(profile)

        logger.info(
            "Style profile updated | samples=%d vocab=%s sentence_pref=%s",
            profile.sample_count,
            profile.vocabulary_level,
            profile.sentence_length_pref,
        )
        return _to_response(profile)

    async def get_profile(self) -> StyleProfileResponse | None:
        """Return the default style profile, or None if not yet built."""
        result = await self._db.execute(
            select(StyleProfile).where(StyleProfile.profile_name == "default")
        )
        profile = result.scalar_one_or_none()
        return _to_response(profile) if profile else None

    async def get_style_hint(self) -> str:
        """
        Return a prompt injection string for the current style profile.
        Returns empty string if no profile exists.
        """
        profile = await self.get_profile()
        if not profile or not profile.style_description:
            return ""

        return (
            f"\nUSER STYLE PROFILE:\n"
            f"- Voice: {profile.style_description}\n"
            f"- Sentence length preference: {profile.sentence_length_pref}\n"
            f"- Vocabulary level: {profile.vocabulary_level}\n"
            f"- Preferred formats: {', '.join(profile.preferred_styles) if profile.preferred_styles else 'none specified'}\n"
            f"Match this writing style closely."
        )


def _parse_style_response(content: str, samples: list[str]) -> dict:
    """Parse LLM style analysis JSON, with fallback to heuristics."""
    json_match = re.search(r"```json\s*([\s\S]+?)\s*```", content)
    raw = json_match.group(1) if json_match else content.strip()

    try:
        data = json.loads(raw)
        return {
            "sentence_length_pref": data.get("sentence_length_pref", "medium"),
            "vocabulary_level": data.get("vocabulary_level", "professional"),
            "avg_post_length": int(data.get("avg_post_length", 0)),
            "preferred_styles": list(data.get("preferred_styles", [])),
            "style_description": str(data.get("style_description", "")).strip(),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Could not parse style JSON — using heuristics.")
        return _heuristic_style(samples)


def _heuristic_style(samples: list[str]) -> dict:
    """Fallback: infer style metrics from text statistics."""
    all_text = " ".join(samples)
    avg_len = avg_sentence_length(all_text)
    avg_words = sum(word_count(s) for s in samples) / max(len(samples), 1)

    if avg_len < 10:
        sentence_pref = "short"
    elif avg_len < 20:
        sentence_pref = "medium"
    else:
        sentence_pref = "long"

    return {
        "sentence_length_pref": sentence_pref,
        "vocabulary_level": "professional",
        "avg_post_length": int(avg_words),
        "preferred_styles": [],
        "style_description": "",
    }


def _to_response(profile: StyleProfile) -> StyleProfileResponse:
    return StyleProfileResponse(
        id=profile.id,
        profile_name=profile.profile_name,
        sentence_length_pref=profile.sentence_length_pref,
        vocabulary_level=profile.vocabulary_level,
        avg_post_length=profile.avg_post_length,
        preferred_styles=profile.preferred_styles or [],
        style_description=profile.style_description or "",
        sample_count=profile.sample_count,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
    )
