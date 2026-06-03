"""
analysis_prompts.py — Prompt templates for post quality analysis
"""

from __future__ import annotations

from app.models.schemas import AnalyzePostRequest

SYSTEM_PROMPT = """You are a LinkedIn content analytics expert who evaluates posts for their engagement potential.

Analyze posts objectively and provide actionable, specific recommendations.

For full analysis, evaluate on these dimensions (0-10):
- hook_strength: How compelling is the first 1-2 sentences? Does it stop the scroll?
- readability: Format, sentence length, paragraph breaks, visual scanability
- authority_signals: Does the author demonstrate credibility through specificity, data, or experience?
- emotional_triggers: Does it evoke curiosity, FOMO, inspiration, challenge, or recognition?
- cta_effectiveness: Does it drive meaningful engagement (comments, saves, shares)?
- overall: Weighted average considering LinkedIn algorithm factors

Be honest — most posts score 4-6. Reserve 8+ for genuinely exceptional content.

OUTPUT FORMAT (JSON):
```json
{
  "scores": {
    "hook_strength": 7,
    "readability": 8,
    "authority_signals": 6,
    "emotional_triggers": 5,
    "cta_effectiveness": 4,
    "overall": 6
  },
  "summary": "One paragraph summarizing the post's strengths and main weakness.",
  "recommendations": [
    "Specific, actionable recommendation 1",
    "Specific, actionable recommendation 2",
    "Specific, actionable recommendation 3"
  ]
}
```

Provide 3-6 concrete, specific recommendations. Avoid vague advice like "make it more engaging"."""


def build_analysis_prompt(request: AnalyzePostRequest) -> tuple[str, str]:
    """Build system and user prompts for post analysis."""

    if request.mode == "summarize":
        user_prompt = f"""Summarize this LinkedIn post in 2-3 sentences, capturing the core message and key insight:

POST:
{request.content}

Return JSON with just a "summary" field. Use score of 5 for all metrics."""
    elif request.mode == "quick":
        user_prompt = f"""Quickly assess this post's overall quality and give the top 2 improvements:

POST:
{request.content}

Return the full JSON format but keep recommendations brief."""
    else:
        user_prompt = f"""Analyze this LinkedIn post in full detail:

POST:
{request.content}

Provide comprehensive scoring and at least 4 specific, actionable recommendations.
Be constructively critical — identify real weaknesses, not just strengths."""

    return SYSTEM_PROMPT, user_prompt
