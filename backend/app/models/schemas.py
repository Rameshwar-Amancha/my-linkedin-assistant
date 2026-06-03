"""
schemas.py — Pydantic v2 request/response models for all API endpoints.

These are the shared API contracts between the extension and backend.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Draft Reply
# ---------------------------------------------------------------------------

ToneType = Literal[
    "professional", "concise", "expert", "contrarian",
    "founder", "recruiter", "thoughtful_question"
]

PersonaType = Literal[
    "senior_engineer", "product_manager", "executive",
    "entrepreneur", "researcher", "consultant"
]


class DraftReplyRequest(BaseModel):
    author_name: str = Field(default="", max_length=200)
    author_role: str = Field(default="", max_length=300)
    post_content: str = Field(default="", max_length=10_000)
    media_context: str = Field(default="", max_length=2000)
    tone: ToneType = "professional"
    persona: PersonaType = "senior_engineer"
    comment_context: str = Field(default="", max_length=2000)

    @field_validator("post_content", "author_name", "author_role", "media_context", mode="before")
    @classmethod
    def strip_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class DraftReplyResponse(BaseModel):
    reply: str
    reasoning: str
    engagement_score: int = Field(ge=0, le=10)
    tone_used: ToneType
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Generate Post
# ---------------------------------------------------------------------------

PostStyleType = Literal[
    "professional", "educational", "founder",
    "technical", "viral", "concise_authority"
]


class GeneratePostRequest(BaseModel):
    topic: str = Field(..., min_length=5, max_length=800)
    style: PostStyleType = "professional"
    tone: ToneType = "professional"
    persona: PersonaType = "senior_engineer"
    variations: int = Field(default=3, ge=1, le=5)
    include_cta: bool = True
    include_hashtags: bool = True
    storytelling_mode: bool = False
    additional_context: str = Field(default="", max_length=1000)

    @field_validator("topic", "additional_context", mode="before")
    @classmethod
    def strip_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class PostVariation(BaseModel):
    content: str
    hashtags: list[str] = []
    engagement_prediction: int = Field(ge=0, le=10)
    word_count: int = 0


class GeneratePostResponse(BaseModel):
    variations: list[PostVariation]
    topic_analyzed: str
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Analyze Post
# ---------------------------------------------------------------------------

class AnalyzePostRequest(BaseModel):
    content: str = Field(..., min_length=20, max_length=5000)
    mode: Literal["full", "summarize", "quick"] = "full"

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class PostScores(BaseModel):
    hook_strength: int = Field(ge=0, le=10)
    readability: int = Field(ge=0, le=10)
    authority_signals: int = Field(ge=0, le=10)
    emotional_triggers: int = Field(ge=0, le=10)
    cta_effectiveness: int = Field(ge=0, le=10)
    overall: int = Field(ge=0, le=10)


class AnalyzePostResponse(BaseModel):
    scores: PostScores
    recommendations: list[str] = []
    summary: str = ""
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

class TrendsQueryParams(BaseModel):
    category: str = ""
    limit: int = Field(default=15, ge=1, le=50)


class TrendItem(BaseModel):
    topic: str
    source: str
    engagement_potential: int = Field(ge=0, le=10)
    recency_score: int = Field(default=5, ge=0, le=10)
    suggested_angle: str = ""
    url: str = ""
    published_at: str = ""


class TrendsResponse(BaseModel):
    trends: list[TrendItem]
    cached: bool = False
    fetched_at: str = ""


# ---------------------------------------------------------------------------
# A/B Testing
# ---------------------------------------------------------------------------

class ABTestRecordRequest(BaseModel):
    topic_hash: str = Field(..., min_length=1, max_length=64)
    style: PostStyleType
    tone: ToneType
    persona: PersonaType
    variation_index: int = Field(default=0, ge=0, le=4)
    engagement_prediction: int = Field(default=5, ge=0, le=10)


class ABTestUpdateActualsRequest(BaseModel):
    record_id: str = Field(default="", max_length=36)  # Set from path param in route
    actual_reactions: int = Field(default=0, ge=0)
    actual_comments: int = Field(default=0, ge=0)


class ABTestSummaryItem(BaseModel):
    style: str
    tone: str
    persona: str
    total_uses: int
    avg_predicted_score: float
    avg_actual_reactions: float
    avg_actual_comments: float


class ABTestSummaryResponse(BaseModel):
    records_analyzed: int
    top_style: str = ""
    top_tone: str = ""
    summary: list[ABTestSummaryItem]


# ---------------------------------------------------------------------------
# Content Calendar (Scheduled Posts)
# ---------------------------------------------------------------------------

class ScheduledPostCreate(BaseModel):
    title: str = Field(default="Untitled", max_length=300)
    content: str = Field(..., min_length=10, max_length=5000)
    scheduled_for: str = Field(..., description="ISO 8601 datetime, e.g. 2025-06-01T09:00:00Z")
    style: PostStyleType = "professional"
    tone: ToneType = "professional"
    persona: PersonaType = "senior_engineer"
    hashtags: list[str] = []
    notes: str = Field(default="", max_length=1000)

    @field_validator("content", "title", "notes", mode="before")
    @classmethod
    def strip_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("scheduled_for")
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("scheduled_for must be a valid ISO 8601 datetime string")
        return v


class ScheduledPostUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    content: str | None = Field(default=None, min_length=10, max_length=5000)
    scheduled_for: str | None = None
    status: str | None = None
    hashtags: list[str] | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ScheduledPostResponse(BaseModel):
    id: str
    title: str
    content: str
    scheduled_for: str
    status: str
    style: str
    tone: str
    persona: str
    hashtags: list[str]
    notes: str
    created_at: str
    updated_at: str


class CalendarResponse(BaseModel):
    posts: list[ScheduledPostResponse]
    total: int


# ---------------------------------------------------------------------------
# Personal Writing Style
# ---------------------------------------------------------------------------

class StyleLearnRequest(BaseModel):
    draft_samples: list[str] = Field(..., min_length=1, description="List of post/reply drafts to learn from")

    @field_validator("draft_samples")
    @classmethod
    def validate_samples(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("At least 1 draft sample required")
        if len(v) > 20:
            raise ValueError("Maximum 20 draft samples allowed")
        return [s.strip() for s in v if s.strip()]


class StyleProfileResponse(BaseModel):
    id: str
    profile_name: str
    sentence_length_pref: str
    vocabulary_level: str
    avg_post_length: int
    preferred_styles: list[str]
    style_description: str
    sample_count: int
    updated_at: str


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

WEBHOOK_EVENTS = Literal[
    "trends_updated",
    "draft_saved",
    "post_generated",
    "reply_generated",
]


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    events: list[str] = Field(..., min_length=1)
    description: str = Field(default="", max_length=200)
    secret: str = Field(default="", max_length=128, description="Optional HMAC secret for payload signing")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v.strip()

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        valid = {"trends_updated", "draft_saved", "post_generated", "reply_generated"}
        for event in v:
            if event not in valid:
                raise ValueError(f"Invalid event '{event}'. Valid: {valid}")
        return v


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    description: str
    is_active: bool
    failure_count: int
    last_triggered_at: str | None
    created_at: str


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]
    total: int


# ---------------------------------------------------------------------------
# Algorithm Score
# ---------------------------------------------------------------------------

class AlgorithmScoreRequest(BaseModel):
    content: str = Field(..., min_length=20, max_length=5000)
    has_media: bool = False
    scheduled_hour: int | None = Field(default=None, ge=0, le=23, description="Hour (0-23) you plan to post")
    scheduled_day: str | None = Field(
        default=None,
        description="Day of week: monday/tuesday/wednesday/thursday/friday/saturday/sunday"
    )

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class AlgorithmScoreResponse(BaseModel):
    algorithm_score: int = Field(ge=0, le=10)
    distribution_tier: str  # local | broad | viral
    hook_score: int = Field(ge=0, le=10)
    virality_score: int = Field(ge=0, le=10)
    word_count: int
    hashtag_count: int
    timing_score: int = Field(ge=0, le=10)
    suggestions: list[str] = []
    first_comment_tip: str = ""
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Growth Optimizer
# ---------------------------------------------------------------------------

class HashtagOptimizeRequest(BaseModel):
    topic: str = Field(..., min_length=5, max_length=500)
    persona: PersonaType = "senior_engineer"
    target_audience: str = Field(default="", max_length=300)

    @field_validator("topic", "target_audience", mode="before")
    @classmethod
    def strip_fields(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class HashtagSuggestion(BaseModel):
    hashtag: str
    estimated_reach: str  # "niche" | "medium" | "broad"
    engagement_level: str  # "low" | "medium" | "high"
    reason: str


class HashtagOptimizeResponse(BaseModel):
    primary_hashtags: list[HashtagSuggestion]  # 3-5 optimal
    secondary_hashtags: list[HashtagSuggestion]  # 5-10 secondary
    avoid_hashtags: list[str] = []  # oversaturated/irrelevant
    recommended_count: int = 5
    tokens_used: int = 0


class OptimalTimingResponse(BaseModel):
    best_days: list[str]  # e.g. ["Tuesday", "Wednesday", "Thursday"]
    best_hours: list[int]  # e.g. [7, 8, 12, 17, 18]
    timezone_note: str
    heatmap: dict[str, list[int]]  # {"monday": [8, 12], "tuesday": [7, 8, 17], ...}
    reasoning: str


class GrowthTip(BaseModel):
    category: str  # "content" | "engagement" | "profile" | "consistency" | "network"
    tip: str
    impact: str  # "high" | "medium" | "low"
    action: str  # specific actionable step


class GrowthTipsResponse(BaseModel):
    tips: list[GrowthTip]
    weekly_focus: str
    follower_growth_levers: list[str]


# ---------------------------------------------------------------------------
# Authority Builder
# ---------------------------------------------------------------------------

class AuthorityAnalyzeRequest(BaseModel):
    post_samples: list[str] = Field(..., min_length=1, description="Recent LinkedIn posts to analyze")
    professional_context: str = Field(default="", max_length=500)

    @field_validator("post_samples")
    @classmethod
    def validate_samples(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("At least 1 post sample required")
        if len(v) > 15:
            raise ValueError("Maximum 15 post samples allowed")
        return [s.strip() for s in v if s.strip()]


class CredibilitySignals(BaseModel):
    uses_data_stats: bool = False
    uses_personal_stories: bool = False
    uses_specific_examples: bool = False
    uses_frameworks: bool = False
    has_contrarian_views: bool = False
    mentions_credentials: bool = False


class AuthorityAnalyzeResponse(BaseModel):
    authority_score: int = Field(ge=0, le=10)
    topic_expertise: list[str]  # ["AI Strategy", "Product Management", ...]
    engagement_tips: list[str]
    credibility_signals: CredibilitySignals
    authority_summary: str
    growth_actions: list[str]  # specific next steps
    tokens_used: int = 0


class EngagementSuggestionsResponse(BaseModel):
    topics_to_comment_on: list[str]
    posting_cadence: str  # e.g. "3x per week"
    engagement_strategy: str
    comment_templates: list[str]  # thoughtful comment starters, not spammy
    authority_building_content: list[str]  # content types that build authority


# ---------------------------------------------------------------------------
# Time Tracking
# ---------------------------------------------------------------------------

class TimeSessionLog(BaseModel):
    session_date: str = Field(..., description="YYYY-MM-DD")
    active_seconds: int = Field(default=0, ge=0)
    idle_seconds: int = Field(default=0, ge=0)
    page_views: int = Field(default=0, ge=0)
    actions_taken: int = Field(default=0, ge=0)
    productive_seconds: int = Field(default=0, ge=0)

    @field_validator("session_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("session_date must be YYYY-MM-DD")
        return v


class TimeTrackingSummaryResponse(BaseModel):
    today_active_minutes: int
    today_productive_minutes: int
    week_active_minutes: int
    week_productive_minutes: int
    daily_breakdown: list[dict]  # [{date, active_minutes, productive_minutes}, ...]
    insights: list[str]
    focus_ratio: float  # productive / total (0.0 - 1.0)
