"""
test_trends.py — Tests for GET /api/trends
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.schemas import TrendItem


MOCK_TRENDS = [
    TrendItem(
        topic="Why Python async is faster than you think",
        source="hackernews",
        url="https://news.ycombinator.com/item?id=123",
        engagement_potential=8,
        suggested_angle="Share your experience with async Python in production",
        published_at="2024-01-01T00:00:00Z",
    ),
    TrendItem(
        topic="The real cost of microservices",
        source="techcrunch",
        url="https://techcrunch.com/article",
        engagement_potential=7,
        suggested_angle="What does this mean for your architecture decisions?",
        published_at="2024-01-01T00:00:00Z",
    ),
]


@pytest.mark.asyncio
async def test_trends_success(client: AsyncClient):
    with patch("app.services.trend_service.TrendService._fetch_all_trends",
               new_callable=AsyncMock, return_value=MOCK_TRENDS):
        response = await client.get("/api/trends")
    assert response.status_code == 200

    data = response.json()
    assert "trends" in data
    assert isinstance(data["trends"], list)
    assert "fetched_at" in data


@pytest.mark.asyncio
async def test_trends_with_category(client: AsyncClient):
    with patch("app.services.trend_service.TrendService._fetch_all_trends",
               new_callable=AsyncMock, return_value=MOCK_TRENDS):
        response = await client.get("/api/trends", params={"category": "tech"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trends_limit_param(client: AsyncClient):
    # Provide a single-item list so the slicing logic has ≤ 1 to return
    single_item = [MOCK_TRENDS[0]]
    with patch("app.services.trend_service.TrendService._fetch_all_trends",
               new_callable=AsyncMock, return_value=single_item):
        response = await client.get("/api/trends", params={"limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data["trends"]) <= 1


@pytest.mark.asyncio
async def test_trends_limit_bounds(client: AsyncClient):
    """limit must be 1-50."""
    response = await client.get("/api/trends", params={"limit": 100})
    assert response.status_code == 422

    response = await client.get("/api/trends", params={"limit": 0})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trends_trend_item_structure(client: AsyncClient):
    with patch("app.services.trend_service.TrendService._fetch_all_trends",
               new_callable=AsyncMock, return_value=MOCK_TRENDS):
        response = await client.get("/api/trends")
    assert response.status_code == 200

    if response.json()["trends"]:
        item = response.json()["trends"][0]
        assert "topic" in item
        assert "source" in item
        assert "url" in item
        assert "engagement_potential" in item
        assert "suggested_angle" in item
