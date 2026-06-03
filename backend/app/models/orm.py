"""
orm.py — SQLAlchemy ORM models

Tables:
- personas: Custom writing personas
- prompt_history: LLM prompt + response log
- saved_drafts: User-saved reply/post drafts
- trend_cache: Cached trend results
- engagement_metrics: Per-post engagement tracking
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    drafts: Mapped[list[SavedDraft]] = relationship("SavedDraft", back_populates="persona")


# ---------------------------------------------------------------------------
# Prompt History
# ---------------------------------------------------------------------------

class PromptHistory(Base):
    __tablename__ = "prompt_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    # Store hashed/anonymized request identifiers — NOT full content
    request_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Saved Drafts
# ---------------------------------------------------------------------------

class SavedDraft(Base):
    __tablename__ = "saved_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    label: Mapped[str] = mapped_column(String(200), default="Draft")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    draft_type: Mapped[str] = mapped_column(String(50), default="reply")  # reply | post
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    persona_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("personas.id"), nullable=True
    )
    engagement_score: Mapped[int] = mapped_column(Integer, default=0)
    post_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    persona: Mapped[Persona | None] = relationship("Persona", back_populates="drafts")


# ---------------------------------------------------------------------------
# Trend Cache
# ---------------------------------------------------------------------------

class TrendCacheEntry(Base):
    __tablename__ = "trend_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    cache_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    topics_json: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Engagement Metrics
# ---------------------------------------------------------------------------

class EngagementMetric(Base):
    __tablename__ = "engagement_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    post_url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    predicted_score: Mapped[int] = mapped_column(Integer, default=0)
    actual_reactions: Mapped[int] = mapped_column(Integer, default=0)
    actual_comments: Mapped[int] = mapped_column(Integer, default=0)
    draft_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# A/B Test Records
# ---------------------------------------------------------------------------

class ABTestRecord(Base):
    __tablename__ = "ab_test_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    topic_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    style: Mapped[str] = mapped_column(String(50), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)
    persona: Mapped[str] = mapped_column(String(50), nullable=False)
    variation_index: Mapped[int] = mapped_column(Integer, default=0)
    engagement_prediction: Mapped[int] = mapped_column(Integer, default=0)
    actual_reactions: Mapped[int] = mapped_column(Integer, default=0)
    actual_comments: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Scheduled Posts (Content Calendar)
# ---------------------------------------------------------------------------

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(300), default="Untitled")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|scheduled|published|cancelled
    style: Mapped[str] = mapped_column(String(50), default="professional")
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    persona: Mapped[str] = mapped_column(String(50), default="senior_engineer")
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Style Profiles (Personal Writing Style)
# ---------------------------------------------------------------------------

class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    profile_name: Mapped[str] = mapped_column(String(100), default="default")
    sentence_length_pref: Mapped[str] = mapped_column(String(20), default="medium")  # short|medium|long
    vocabulary_level: Mapped[str] = mapped_column(String(20), default="professional")  # casual|professional|technical
    avg_post_length: Mapped[int] = mapped_column(Integer, default=0)
    preferred_styles: Mapped[list] = mapped_column(JSON, default=list)
    style_description: Mapped[str] = mapped_column(Text, default="")  # LLM-generated style summary
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Webhook Subscriptions
# ---------------------------------------------------------------------------

class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["trends_updated", "draft_saved"]
    secret: Mapped[str] = mapped_column(String(128), default="")  # HMAC signing secret
    description: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Algorithm Score Records
# ---------------------------------------------------------------------------

class AlgorithmScoreRecord(Base):
    __tablename__ = "algorithm_score_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    algorithm_score: Mapped[int] = mapped_column(Integer, default=0)
    distribution_tier: Mapped[str] = mapped_column(String(20), default="local")  # local|broad|viral
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    hashtag_count: Mapped[int] = mapped_column(Integer, default=0)
    has_media: Mapped[bool] = mapped_column(Boolean, default=False)
    has_cta: Mapped[bool] = mapped_column(Boolean, default=False)
    hook_score: Mapped[int] = mapped_column(Integer, default=0)
    virality_score: Mapped[int] = mapped_column(Integer, default=0)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    scored_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Authority Records
# ---------------------------------------------------------------------------

class AuthorityRecord(Base):
    __tablename__ = "authority_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    authority_score: Mapped[int] = mapped_column(Integer, default=0)
    topic_expertise: Mapped[list] = mapped_column(JSON, default=list)  # ["AI", "Leadership", ...]
    engagement_tips: Mapped[list] = mapped_column(JSON, default=list)
    credibility_signals: Mapped[dict] = mapped_column(JSON, default=dict)  # {data_usage, specificity, ...}
    post_count_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Time Tracking Sessions (LinkedIn usage time — extension-reported)
# ---------------------------------------------------------------------------

class TimeTrackingSession(Base):
    __tablename__ = "time_tracking_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    active_seconds: Mapped[int] = mapped_column(Integer, default=0)
    idle_seconds: Mapped[int] = mapped_column(Integer, default=0)
    page_views: Mapped[int] = mapped_column(Integer, default=0)
    actions_taken: Mapped[int] = mapped_column(Integer, default=0)  # AI assists used
    productive_seconds: Mapped[int] = mapped_column(Integer, default=0)  # time using AI tools
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
