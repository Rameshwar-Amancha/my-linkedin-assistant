"""
post_prompts.py — Prompt templates for LinkedIn post generation

Designed to produce posts that:
- Have strong hooks (first line stops the scroll)
- Use LinkedIn-optimal formatting (short paragraphs, line breaks)
- Avoid AI-detectable patterns
- Drive authentic engagement through conversation, not clickbait
"""

from __future__ import annotations

from app.models.schemas import GeneratePostRequest

# ---------------------------------------------------------------------------
# Style guides
# ---------------------------------------------------------------------------

STYLE_GUIDES = {
    "professional": """
STYLE: Professional authority
- Lead with a bold, specific claim or counterintuitive insight
- Use short paragraphs (1-3 sentences max)
- Include a specific data point, example, or analogy
- End with an open question or CTA
- Tone: Confident, direct, not stuffy
""",
    "educational": """
STYLE: Educational / How-to
- Open with a problem statement or surprising fact
- Structure as a numbered list or step-by-step framework
- Each point should be actionable
- Close with a summary insight
- Tone: Clear, helpful, no jargon
""",
    "founder": """
STYLE: Founder story
- Open with a personal moment or specific decision point
- Tell a brief story arc: challenge → insight → outcome
- Make it vulnerable and real — not a highlight reel
- Extract a transferable lesson
- Tone: Authentic, first-person, conversational
""",
    "technical": """
STYLE: Technical deep dive
- Open with a specific technical problem or architectural decision
- Use precise language — avoid dumbing down
- Include concrete examples, pseudocode, or system diagrams (described in text)
- Acknowledge tradeoffs and limitations
- Tone: Engineer-to-engineer, intellectually honest
""",
    "viral": """
STYLE: Hook-first / viral
- First line MUST be a scroll-stopper: surprising statistic, bold claim, or provocative question
- Use short punchy lines — maximum 10 words per line
- Build curiosity through the post — pay it off at the end
- Use the "breadcrumb" format: each line makes you want to read the next
- Tone: Bold, direct, slightly provocative but not clickbait
""",
    "concise_authority": """
STYLE: Concise authority
- 150-200 words maximum
- Every sentence must earn its place — zero filler
- State a strong opinion or insight in the first line
- Build the argument in 3-4 tight sentences
- End with a memorable closing line
- Tone: Dense, confident, no wasted words
""",
}

# ---------------------------------------------------------------------------
# Persona voice additions
# ---------------------------------------------------------------------------

PERSONA_VOICES = {
    "senior_engineer": "Write with the voice of a senior engineer — reference real technical decisions, tradeoffs, and lessons from production.",
    "product_manager": "Write from a PM perspective — focus on user outcomes, metrics, and cross-functional dynamics.",
    "executive": "Write with executive gravitas — strategic framing, big-picture thinking, organizational insight.",
    "entrepreneur": "Write as a founder — candid, from lived experience, with lessons from building things.",
    "researcher": "Write with research credibility — cite patterns, question assumptions, show intellectual rigor.",
    "consultant": "Write as a consultant — bring cross-industry perspective, structured thinking, actionable frameworks.",
}

# ---------------------------------------------------------------------------
# Anti-patterns
# ---------------------------------------------------------------------------

ANTI_PATTERNS_POST = """
AVOID:
- Generic LinkedIn openings ("I'm excited to share...", "Thrilled to announce...")
- AI-generated filler ("In today's fast-paced world...", "Now more than ever...")
- Hollow motivational statements without substance
- Overused hashtag lists (max 3-5 relevant hashtags)
- "Let me know in the comments" as the only CTA
- Padding to hit a word count
- Starting with "I" (vary sentence openers)
"""

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert LinkedIn content strategist and ghostwriter.
You create posts that generate genuine engagement through substance, authenticity, and craft.

Your posts are read by professionals who can detect generic AI content instantly.
Write like a real person who has lived through the topic.

{anti_patterns}

OUTPUT FORMAT:
Return a JSON array of {count} post variations:
```json
[
  {{
    "content": "Full post text with proper line breaks (use \\n for line breaks)",
    "hashtags": ["#relevant", "#hashtags", "#here"],
    "engagement_prediction": 7
  }}
]
```

engagement_prediction: 1-10 estimate of LinkedIn engagement quality.
Each variation should take a meaningfully different angle on the topic."""


def build_post_prompt(
    request: GeneratePostRequest,
    count: int,
    offset: int = 0,
    style_hint: str = "",
) -> tuple[str, str]:
    """
    Build system and user prompts for post generation.

    Args:
        request: Post generation request
        count: Number of variations to generate in this batch
        offset: Variation number offset (for generating batches > 3)
        style_hint: Optional personal style profile injection string

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    style_guide = STYLE_GUIDES.get(request.style, STYLE_GUIDES["professional"])
    persona_voice = PERSONA_VOICES.get(request.persona, "")

    system_prompt = SYSTEM_PROMPT.format(
        count=count,
        anti_patterns=ANTI_PATTERNS_POST,
    )

    cta_instruction = "Include a compelling call-to-action at the end." if request.include_cta else "No CTA needed."
    hashtag_instruction = "Include 3-5 highly relevant hashtags." if request.include_hashtags else "Do not include hashtags."
    story_instruction = "Use a storytelling structure with narrative arc." if request.storytelling_mode else ""
    offset_instruction = f"These are variations {offset + 1} to {offset + count} — make them meaningfully different from the obvious approaches." if offset > 0 else ""

    user_prompt = f"""Generate {count} LinkedIn post variation(s) about:

TOPIC: {request.topic}

{style_guide.strip()}

PERSONA VOICE: {persona_voice}

ADDITIONAL INSTRUCTIONS:
- {cta_instruction}
- {hashtag_instruction}
{f'- {story_instruction}' if story_instruction else ''}
{f'- {offset_instruction}' if offset_instruction else ''}
{f'- Additional context: {request.additional_context}' if request.additional_context else ''}
{style_hint}

Target: 150-400 words (unless style guide specifies otherwise).
Format line breaks as \\n in the JSON content field.
Make each variation distinctly different in angle and structure."""

    return system_prompt, user_prompt
