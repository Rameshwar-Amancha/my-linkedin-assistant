"""
test_algorithm.py — Tests for POST /api/algorithm/score
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.llm.base import LLMResponse


MOCK_ALGO_JSON = json.dumps({
    "algorithm_score": 7.5,
    "distribution_tier": "broad",
    "hook_score": 8.0,
    "virality_score": 7.0,
    "timing_score": 8.0,
    "suggestions": [
        "Add a compelling question at the end.",
        "Break into shorter paragraphs.",
    ],
    "first_comment_tip": "Pin a comment with a resource link within 5 minutes of posting.",
})


@pytest.fixture
def mock_algo_llm(mock_llm_provider):
    _resp = LLMResponse(
        content=MOCK_ALGO_JSON,
        prompt_tokens=100, completion_tokens=80, total_tokens=180,
        model="test-model", provider="test", latency_ms=200,
    )
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=_resp)
    mock_llm_provider.generate = AsyncMock(return_value=_resp)
    return mock_llm_provider


@pytest.mark.asyncio
async def test_algorithm_score_success(app, mock_algo_llm, monkeypatch):
    import app.services.algorithm_service as alg
    monkeypatch.setattr(alg, "get_llm_provider", lambda: mock_algo_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.post("/api/algorithm/score", json={
            "content": "I spent 5 years learning the wrong things. Here's what I wish I knew earlier.\n\n1. Systems over goals.\n2. Output over activity.\n3. Network compounds.\n\nWhat would you add?",
            "has_media": False,
            "scheduled_day": "tuesday",
            "scheduled_hour": 8,
        })

    assert response.status_code == 200
    data = response.json()
    assert "algorithm_score" in data
    assert 0 <= data["algorithm_score"] <= 10
    assert "distribution_tier" in data
    assert data["distribution_tier"] in ("local", "broad", "viral")
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert "word_count" in data
    assert "hashtag_count" in data


@pytest.mark.asyncio
async def test_algorithm_score_short_content(client: AsyncClient):
    response = await client.post("/api/algorithm/score", json={"content": "Too short"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_algorithm_score_no_timing(app, mock_algo_llm, monkeypatch):
    """Score without scheduling info — timing defaults to 5."""
    import app.services.algorithm_service as alg
    monkeypatch.setattr(alg, "get_llm_provider", lambda: mock_algo_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.post("/api/algorithm/score", json={
            "content": "Here are the top 5 lessons from scaling a startup from 0 to 1M users." * 3,
        })
    assert response.status_code == 200
    data = response.json()
    assert data["timing_score"] == 5.0
