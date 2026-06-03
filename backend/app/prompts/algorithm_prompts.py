"""
algorithm_prompts.py — Prompts for LinkedIn algorithm scoring and authority analysis.
"""

from __future__ import annotations

from app.llm.base import LLMRequest


def algorithm_score_prompt(
    content: str,
    word_count: int,
    hashtag_count: int,
    has_media: bool,
    scheduled_hour: int | None,
    scheduled_day: str | None,
) -> LLMRequest:
    """Return prompt for scoring a post against the LinkedIn algorithm."""
    system = (
        "You are a LinkedIn algorithm expert. You understand exactly how LinkedIn's "
        "feed algorithm distributes content in 2025-2026: the 3-tier model (local network → "
        "broader network → viral), dwell time signals, early engagement velocity, "
        "hook strength, content format penalties/bonuses, and posting time windows. "
        "Score objectively. Return valid JSON only."
    )

    timing_clause = ""
    if scheduled_day and scheduled_hour is not None:
        timing_clause = f"\nPlanned posting time: {scheduled_day} at {scheduled_hour:02d}:00"
    elif scheduled_hour is not None:
        timing_clause = f"\nPlanned posting hour: {scheduled_hour:02d}:00"

    user = f"""Score this LinkedIn post for algorithm distribution potential.

Post content:
\"\"\"
{content}
\"\"\"

Post metadata:
- Word count: {word_count}
- Hashtag count: {hashtag_count}
- Has media (image/video/PDF): {has_media}{timing_clause}

Return JSON in EXACTLY this format:
{{
  "algorithm_score": 7,
  "distribution_tier": "local|broad|viral",
  "hook_score": 8,
  "virality_score": 6,
  "timing_score": 7,
  "suggestions": [
    "Specific improvement 1",
    "Specific improvement 2"
  ],
  "first_comment_tip": "What to post as your first comment within 5 minutes of publishing to boost early engagement velocity"
}}

Scoring criteria:
- algorithm_score (0-10): overall likelihood of broad distribution
- distribution_tier: local (friends/connections only), broad (2nd/3rd degree), viral (beyond network)
- hook_score (0-10): first 1-2 lines — does it create a pattern interrupt or curiosity gap?
- virality_score (0-10): shareability, save-worthiness, comment-bait quality
- timing_score (0-10): if timing provided, score it; otherwise assume user will post at a reasonable time
- suggestions: 3–5 specific, actionable improvements (not generic)
- first_comment_tip: a strategic first comment that adds value and boosts early engagement signal

LinkedIn algorithm factors (weight them accordingly):
- Word count: 150-300 is optimal for text posts
- Hashtags: 3-5 is optimal; >10 is penalized
- No external links in post body (put in comments instead) — big penalty
- Native media (uploaded images/videos) get boost; link previews do not
- Posting Tue-Thu between 7-9am or 5-7pm local time gets 20-40% more reach
- First line must hook — users see only 2 lines before "see more"
- Questions at the end boost comments; lists boost saves"""

    return LLMRequest(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=800,
        temperature=0.3,
    )


def authority_analyze_prompt(posts_combined: str, professional_context: str) -> LLMRequest:
    """Return prompt for authority/influence analysis from post samples."""
    system = (
        "You are a LinkedIn personal branding expert and authority-building strategist. "
        "You analyze content to identify thought leadership signals, topic expertise areas, "
        "and credibility patterns. You give specific, actionable authority-building advice. "
        "Return valid JSON only."
    )

    context_clause = f"\nProfessional context: {professional_context}" if professional_context else ""

    user = f"""Analyze these LinkedIn posts to assess thought leadership authority.{context_clause}

Posts:
\"\"\"
{posts_combined}
\"\"\"

Return JSON in EXACTLY this format:
{{
  "authority_score": 7,
  "topic_expertise": ["Topic 1", "Topic 2", "Topic 3"],
  "engagement_tips": [
    "Specific engagement tip 1",
    "Specific engagement tip 2"
  ],
  "credibility_signals": {{
    "uses_data_stats": true,
    "uses_personal_stories": true,
    "uses_specific_examples": false,
    "uses_frameworks": false,
    "has_contrarian_views": false,
    "mentions_credentials": true
  }},
  "authority_summary": "2-3 sentence summary of current authority positioning",
  "growth_actions": [
    "Specific action 1 to increase authority",
    "Specific action 2"
  ]
}}

Authority score criteria (0-10):
- 0-3: No clear positioning, generic content
- 4-6: Some expertise signals, inconsistent POV
- 7-8: Clear niche, consistent voice, credibility signals present
- 9-10: Thought leader, strong POV, data-backed, community builder

Identify: top 3-5 topic areas where they show expertise.
Give 4-6 practical engagement tips tailored to their current style.
Give 3-5 specific growth actions they can take this month."""

    return LLMRequest(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1000,
        temperature=0.4,
    )


def engagement_suggestions_prompt(topic_expertise: list[str], authority_score: int) -> LLMRequest:
    """Return prompt for engagement strategy suggestions."""
    system = (
        "You are a LinkedIn engagement strategist. You know that strategic commenting "
        "on the right posts builds more authority than posting alone. "
        "Return valid JSON only."
    )

    topics_str = ", ".join(topic_expertise) if topic_expertise else "general professional topics"

    user = f"""Generate a LinkedIn engagement strategy for someone with:
- Topic expertise: {topics_str}
- Current authority score: {authority_score}/10

Return JSON in EXACTLY this format:
{{
  "topics_to_comment_on": [
    "Specific topic or post type to comment on",
    "Another topic or post type"
  ],
  "posting_cadence": "e.g. 3x per week: Mon/Wed/Fri",
  "engagement_strategy": "2-3 sentence strategy overview",
  "comment_templates": [
    "Template starter that adds genuine value (not a compliment)",
    "Another thoughtful comment starter"
  ],
  "authority_building_content": [
    "Content type that builds authority for this person",
    "Another content type"
  ]
}}

Rules:
- topics_to_comment_on: 5 specific content types/topics to engage with (not accounts)
- comment_templates: 4-6 genuine value-adding comment starters (never sycophantic)
- authority_building_content: 4-5 content formats that would build their specific authority"""

    return LLMRequest(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=700,
        temperature=0.5,
    )
