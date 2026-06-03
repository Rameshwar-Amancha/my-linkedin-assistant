"""
test_post.py — Tests for POST /api/generate-post
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.llm.base import LLMResponse


MOCK_VARIATIONS_JSON = json.dumps([
    {
        "content": "Async Python transformed how we build APIs.\n\nHere's why it matters:\n\n1. Non-blocking I/O handles 10x more connections\n2. FastAPI + async = blazing performance\n3. The mental model takes time but pays off\n\nHave you made the switch yet?",
        "hashtags": ["#Python", "#FastAPI", "#Backend"],
        "engagement_prediction": 7,
    }
])


@pytest.fixture
def mock_post_llm(mock_llm_provider):
    mock_llm_provider.generate_with_timing = AsyncMock(return_value=LLMResponse(
        content=f"```json\n{MOCK_VARIATIONS_JSON}\n```",
        prompt_tokens=200,
        completion_tokens=150,
        total_tokens=350,
        model="test-model",
        provider="test",
        latency_ms=300,
    ))
    return mock_llm_provider


@pytest.mark.asyncio
async def test_generate_post_success(client: AsyncClient, generate_post_payload: dict, mock_post_llm):
    response = await client.post("/api/generate-post", json=generate_post_payload)
    assert response.status_code == 200

    data = response.json()
    assert "variations" in data
    assert len(data["variations"]) >= 1
    assert data["tokens_used"] >= 0
    assert "topic_analyzed" in data


@pytest.mark.asyncio
async def test_generate_post_variation_structure(client: AsyncClient, generate_post_payload: dict, mock_post_llm):
    response = await client.post("/api/generate-post", json=generate_post_payload)
    assert response.status_code == 200

    variation = response.json()["variations"][0]
    assert "content" in variation
    assert "hashtags" in variation
    assert isinstance(variation["hashtags"], list)
    assert 0 <= variation["engagement_prediction"] <= 10
    assert variation["word_count"] > 0


@pytest.mark.asyncio
async def test_generate_post_missing_topic(client: AsyncClient):
    response = await client.post("/api/generate-post", json={
        "style": "professional",
        "persona": "senior_engineer",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_post_all_styles(client: AsyncClient, generate_post_payload: dict, mock_post_llm):
    styles = ["professional", "educational", "founder", "technical", "viral", "concise_authority"]
    for style in styles:
        payload = {**generate_post_payload, "style": style}
        response = await client.post("/api/generate-post", json=payload)
        assert response.status_code == 200, f"Style {style} failed: {response.text}"
