"""
conftest.py — pytest fixtures for all tests
"""

from __future__ import annotations

# Set required env vars BEFORE any app module is imported.
# pydantic-settings reads these at Settings() construction time.
import os
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
# Use in-memory SQLite for tests (isolated per run)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.llm.base import LLMResponse


# ---------------------------------------------------------------------------
# Mock LLM provider
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.build_messages = MagicMock(return_value=[])
    provider.generate_with_timing = AsyncMock(return_value=LLMResponse(
        content='{"reply": "Test reply", "reasoning": "Test reasoning", "engagement_score": 7}',
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model="test-model",
        provider="test",
        latency_ms=200,
    ))
    return provider


# ---------------------------------------------------------------------------
# App with mocked LLM + lifespan (triggers init_db so tables exist)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app(mock_llm_provider, monkeypatch) -> AsyncGenerator[FastAPI, None]:
    # Patch get_llm_provider in every service module that uses it directly.
    for module_path in (
        "app.services.reply_service",
        "app.services.post_service",
        "app.services.analysis_service",
        "app.services.style_service",
    ):
        monkeypatch.setattr(f"{module_path}.get_llm_provider", lambda: mock_llm_provider)

    # Clear the settings cache so a fresh Settings() is built with test env vars
    from app.config.settings import get_settings
    get_settings.cache_clear()

    from main import create_application
    application = create_application()

    # LifespanManager triggers the @asynccontextmanager lifespan (runs init_db)
    async with LifespanManager(application) as manager:
        yield manager.app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Sample request payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def draft_reply_payload() -> dict:
    return {
        "author_name": "Jane Doe",
        "author_role": "CTO at Acme",
        "post_content": "We just shipped our new AI feature after 6 months of work. The key lesson: talk to users early.",
        "tone": "professional",
        "persona": "senior_engineer",
    }


@pytest.fixture
def generate_post_payload() -> dict:
    return {
        "topic": "Why async Python matters for API performance",
        "style": "technical",
        "persona": "senior_engineer",
        "variations": 2,
        "include_cta": True,
        "include_hashtags": True,
        "storytelling_mode": False,
    }


@pytest.fixture
def analyze_post_payload() -> dict:
    return {
        "content": "We doubled revenue last quarter. Here's what we learned:\n\n1. Talk to users weekly\n2. Ship fast, learn faster\n3. Say no to distractions\n\nWhat's your biggest growth lesson?",
        "mode": "full",
    }
