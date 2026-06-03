"""
test_authority.py — Tests for authority analysis endpoints
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.llm.base import LLMResponse


MOCK_AUTHORITY_JSON = json.dumps({
    "authority_score": 7,
    "topic_expertise": ["Python", "System Design", "Engineering Leadership"],
    "engagement_tips": ["Ask a question at the end.", "Share personal failures."],
    "credibility_signals": {
        "uses_data_stats": True,
        "uses_personal_stories": True,
        "uses_specific_examples": True,
        "uses_frameworks": False,
        "has_contrarian_views": False,
        "mentions_credentials": False,
    },
    "authority_summary": "You write with clarity and authority on backend engineering topics.",
    "growth_actions": ["Post a 10-lesson framework post.", "Publish a weekly insight series."],
})

MOCK_ENGAGEMENT_JSON = json.dumps({
    "topics_to_comment_on": ["AI in engineering", "Python concurrency", "Remote work culture"],
    "posting_cadence": "3x per week (Mon/Wed/Fri)",
    "engagement_strategy": "Engage in comments within first 60 min of posting to boost distribution.",
    "comment_templates": [
        "Great point — I've seen this first-hand when [your experience]. What's your take on [follow-up]?",
        "This resonates. The key insight I'd add is [your insight].",
    ],
    "authority_building_content": ["How-to carousels", "Lessons learned posts", "Tool recommendations"],
})

SAMPLE_POST = (
    "Here's what nobody tells you about microservices:\n\n"
    "After running a monolith for 3 years, we split into 12 services.\n"
    "Result? Deployment complexity tripled.\n"
    "Lesson: split by team boundary, not feature.\n"
    "What's your experience?"
)


@pytest.fixture
def mock_authority_llm(mock_llm_provider):
    _resp = LLMResponse(
        content=MOCK_AUTHORITY_JSON,
        prompt_tokens=200, completion_tokens=100, total_tokens=300,
        model="test-model", provider="test", latency_ms=300,
    )
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=_resp)
    mock_llm_provider.generate = AsyncMock(return_value=_resp)
    return mock_llm_provider


@pytest.fixture
def mock_engagement_llm(mock_llm_provider):
    _resp = LLMResponse(
        content=MOCK_ENGAGEMENT_JSON,
        prompt_tokens=100, completion_tokens=80, total_tokens=180,
        model="test-model", provider="test", latency_ms=200,
    )
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=_resp)
    mock_llm_provider.generate = AsyncMock(return_value=_resp)
    return mock_llm_provider


@pytest.mark.asyncio
async def test_analyze_authority_success(app, mock_authority_llm, monkeypatch):
    import app.services.authority_service as auth
    monkeypatch.setattr(auth, "get_llm_provider", lambda: mock_authority_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.post("/api/authority/analyze", json={
            "post_samples": [SAMPLE_POST],
            "professional_context": "Senior backend engineer at a fintech startup.",
        })

    assert response.status_code == 200
    data = response.json()
    assert "authority_score" in data
    assert 0 <= data["authority_score"] <= 10
    assert "topic_expertise" in data
    assert isinstance(data["topic_expertise"], list)
    assert "credibility_signals" in data
    assert "authority_summary" in data
    assert "growth_actions" in data


@pytest.mark.asyncio
async def test_analyze_authority_no_samples(client: AsyncClient):
    response = await client.post("/api/authority/analyze", json={"post_samples": []})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_engagement_suggestions(app, mock_engagement_llm, monkeypatch):
    import app.services.authority_service as auth
    monkeypatch.setattr(auth, "get_llm_provider", lambda: mock_engagement_llm)

    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-secret-key-for-testing"},
    ) as c:
        response = await c.get("/api/authority/suggestions?topics=Python,Engineering&authority_score=7")

    assert response.status_code == 200
    data = response.json()
    assert "topics_to_comment_on" in data
    assert "posting_cadence" in data
    assert "comment_templates" in data
    assert isinstance(data["comment_templates"], list)
