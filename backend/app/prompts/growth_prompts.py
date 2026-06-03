"""
growth_prompts.py — Prompts for follower growth and hashtag optimization.
"""

from __future__ import annotations

from app.llm.base import LLMRequest


def hashtag_optimize_prompt(topic: str, persona: str, target_audience: str) -> LLMRequest:
    """Return system + user prompt for hashtag optimization."""
    system = (
        "You are a LinkedIn growth strategist with deep knowledge of hashtag strategy. "
        "You understand LinkedIn's algorithm, hashtag reach tiers, and which hashtags "
        "attract quality followers vs. vanity metrics. "
        "Always return valid JSON only — no markdown, no explanation outside the JSON."
    )

    audience_clause = f" targeting {target_audience}" if target_audience else ""
    persona_map = {
        "senior_engineer": "a senior software engineer / tech leader",
        "product_manager": "a product manager",
        "executive": "a C-suite executive",
        "entrepreneur": "a founder or entrepreneur",
        "researcher": "a researcher or academic",
        "consultant": "a consultant or advisor",
    }
    persona_label = persona_map.get(persona, "a professional")

    user = f"""Optimize hashtags for a LinkedIn post by {persona_label}{audience_clause}.

Topic: {topic}

Return JSON in EXACTLY this format:
{{
  "primary_hashtags": [
    {{"hashtag": "#example", "estimated_reach": "niche|medium|broad", "engagement_level": "low|medium|high", "reason": "why this hashtag"}}
  ],
  "secondary_hashtags": [
    {{"hashtag": "#example", "estimated_reach": "niche|medium|broad", "engagement_level": "low|medium|high", "reason": "why this hashtag"}}
  ],
  "avoid_hashtags": ["#oversaturated1", "#irrelevant2"],
  "recommended_count": 5
}}

Rules:
- primary_hashtags: 3–5 hashtags (best signal-to-noise ratio for this topic)
- secondary_hashtags: 5–8 additional relevant options
- avoid_hashtags: hashtags that are oversaturated (>10M posts) or generic spam traps
- Niche hashtags (100K–2M posts) outperform broad ones on LinkedIn
- Mix one broad + three niche + one brand/community hashtag for best reach
- Never suggest #LinkedIn, #Networking, #Motivation — these are spam-associated"""

    return LLMRequest(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=800,
        temperature=0.3,
    )


def growth_tips_prompt(style_description: str, post_count: int) -> LLMRequest:
    """Return prompt for personalized follower growth tips."""
    system = (
        "You are a LinkedIn growth expert who has helped hundreds of professionals "
        "grow from 0 to 10K+ followers organically. You give specific, actionable advice "
        "grounded in how the LinkedIn algorithm actually works in 2025-2026. "
        "Never give generic advice. Always be specific and tactical. "
        "Return valid JSON only."
    )

    style_clause = f"\nUser's writing style: {style_description}" if style_description else ""
    post_clause = f"\nUser has created {post_count} posts so far." if post_count > 0 else ""

    user = f"""Generate personalized LinkedIn follower growth tips.{style_clause}{post_clause}

Return JSON in EXACTLY this format:
{{
  "tips": [
    {{
      "category": "content|engagement|profile|consistency|network",
      "tip": "specific tip",
      "impact": "high|medium|low",
      "action": "concrete next action to take today"
    }}
  ],
  "weekly_focus": "one primary focus for this week",
  "follower_growth_levers": ["lever1", "lever2", "lever3"]
}}

Include 8–10 tips covering: content strategy, engagement rhythm, profile optimization,
consistency systems, and network expansion. Prioritize high-impact tips first.

Key 2025-2026 LinkedIn algorithm insights to incorporate:
- Comments in first 60 minutes are the #1 growth signal
- Creator mode + newsletter followers compound reach
- Carousels (PDFs) still get 3x organic reach vs text-only
- Polls get high impressions but low authority transfer
- Engaging on 5 relevant posts before your own post boosts distribution
- Profile completeness affects search ranking
- Consistency (3x/week) beats virality chasing"""

    return LLMRequest(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
        temperature=0.5,
    )
