"""
test_growth.py — Tests for growth optimizer endpoints
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.llm.base import LLMResponse


MOCK_HASHTAG_JSON = json.dumps({
    "primary_hashtags": [
        {"hashtag": "#MachineLearning", "estimated_reach": "medium", "engagement_level": "high", "reason": "Active ML community"},
        {"hashtag": "#AIEngineering", "estimated_reach": "niche", "engagement_level": "high", "reason": "Targeted niche"},
    ],
    "secondary_hashtags": [
        {"hashtag": "#DataScience", "estimated_reach": "broad", "engagement_level": "medium", "reason": "Broad reach"},
    ],
    "avoid_hashtags": ["#AI", "#Tech"],
    "recommended_count": 3,
})

MOCK_TIPS_JSON = json.dumps({
    "tips": [
        {"category": "content", "tip": "Post carousels for higher engagement.", "impact": "high", "action": "Convert your next post to a carousel."},
        {"category": "engagement", "tip": "Comment on 5 posts per day.", "impact": "medium", "action": "Set a 15-min comment block each morning."},
    ],
    "weekly_focus": "Focus on carousel content this week.",
    "follower_growth_levers": ["Consistent cadence", "Niche hashtags", "Early comments"],
})


@pytest.fixture
def mock_hashtag_llm(mock_llm_provider):
    _resp = LLMResponse(
        content=MOCK_HASHTAG_JSON,
        prompt_tokens=80, completion_tokens=60, total_tokens=140,
        model="test-model", provider="test", latency_ms=150,
    )
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=_resp)
    mock_llm_provider.generate = AsyncMock(return_value=_resp)
    return mock_llm_provider


@pytest.fixture
def mock_tips_llm(mock_llm_provider):
    _resp = LLMResponse(
        content=MOCK_TIPS_JSON,
        prompt_tokens=80, completion_tokens=80, total_tokens=160,
        model="test-model", provider="test", latency_ms=150,
    )
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=_resp)
    mock_llm_provider.generate = AsyncMock(return_value=_resp)
    return mock_llm_provider


@pytest.mark.asyncio
async def test_optimal_times_returns_heatmap(client: AsyncClient):
    response = await client.get("/api/growth/optimal-times")
    assert response.status_code == 200
    data = response.json()
    assert "best_days" in data
    assert "best_hours" in data
    assert "heatmap" in data
    assert isinstance(data["best_days"], list)
    assert isinstance(data["best_hours"], list)
    assert "tuesday" in data["best_days"] or len(data["best_days"]) > 0


@pytest.mark.asyncio
async def test_hashtag_optimize(app, mock_hashtag_llm, monkeypatch):
    import app.services.growth_service as gs
    monkeypatch.setattr(gs, "get_llm_provider", lambda: mock_hashtag_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.post("/api/growth/hashtag-optimize", json={
            "topic": "machine learning for engineers",
            "target_audience": "software engineers",
        })
    assert response.status_code == 200
    data = response.json()
    assert "primary_hashtags" in data
    assert len(data["primary_hashtags"]) >= 1
    assert "hashtag" in data["primary_hashtags"][0]
    assert "avoid_hashtags" in data


@pytest.mark.asyncio
async def test_hashtag_optimize_missing_topic(client: AsyncClient):
    response = await client.post("/api/growth/hashtag-optimize", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_growth_tips(app, mock_tips_llm, monkeypatch):
    import app.services.growth_service as gs
    monkeypatch.setattr(gs, "get_llm_provider", lambda: mock_tips_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.get("/api/growth/tips")
    assert response.status_code == 200
    data = response.json()
    assert "tips" in data
    assert len(data["tips"]) >= 1
    assert "category" in data["tips"][0]
    assert "weekly_focus" in data


@pytest.mark.asyncio
async def test_requires_api_key(client: AsyncClient):
    from httpx import AsyncClient, ASGITransport
    # Make a direct call without auth header by building a raw client
    response = await client.get(
        "/api/growth/optimal-times",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403
