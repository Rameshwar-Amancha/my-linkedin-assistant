"""
test_reply.py — Tests for POST /api/draft-reply
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.llm.base import LLMResponse


@pytest.mark.asyncio
async def test_draft_reply_success(client: AsyncClient, draft_reply_payload: dict):
    response = await client.post("/api/draft-reply", json=draft_reply_payload)
    assert response.status_code == 200

    data = response.json()
    assert "reply" in data
    assert "reasoning" in data
    assert "engagement_score" in data
    assert 0 <= data["engagement_score"] <= 10
    assert data["tone_used"] == draft_reply_payload["tone"]
    assert data["tokens_used"] >= 0


@pytest.mark.asyncio
async def test_draft_reply_missing_content(client: AsyncClient):
    response = await client.post("/api/draft-reply", json={
        "author_name": "Jane",
        # Missing required post_content
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_draft_reply_unauthorized(mock_llm_provider, monkeypatch):
    """Request without API key should be rejected."""
    for module_path in ("app.services.reply_service", "app.services.post_service", "app.services.analysis_service"):
        monkeypatch.setattr(f"{module_path}.get_llm_provider", lambda: mock_llm_provider)
    from app.config.settings import get_settings
    get_settings.cache_clear()

    from httpx import ASGITransport, AsyncClient as RawClient
    from main import create_application
    app = create_application()
    async with RawClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.post("/api/draft-reply", json={
            "post_content": "Test post content here for testing",
            "tone": "professional",
            "persona": "senior_engineer",
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_draft_reply_all_tones(client: AsyncClient, draft_reply_payload: dict):
    """Test each supported tone value is accepted."""
    tones = ["professional", "concise", "expert", "contrarian", "founder",
             "recruiter", "thoughtful_question"]
    for tone in tones:
        payload = {**draft_reply_payload, "tone": tone}
        response = await client.post("/api/draft-reply", json=payload)
        assert response.status_code == 200, f"Tone {tone} failed: {response.text}"


@pytest.mark.asyncio
async def test_draft_reply_service_unavailable(client: AsyncClient, draft_reply_payload: dict):
    """LLM failure should return 503."""
    with patch("app.services.reply_service.ReplyService.generate_reply",
               new_callable=AsyncMock,
               side_effect=RuntimeError("LLM service down")):
        response = await client.post("/api/draft-reply", json=draft_reply_payload)
    assert response.status_code == 503
