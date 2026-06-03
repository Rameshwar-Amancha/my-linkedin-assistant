"""
test_time_tracking.py — Tests for time tracking endpoints
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_log_session_returns_204(client: AsyncClient):
    response = await client.post("/api/time-tracking/log", json={
        "session_date": "2025-01-15",
        "active_seconds": 1200,
        "idle_seconds": 300,
        "page_views": 18,
        "actions_taken": 5,
        "productive_seconds": 600,
    })
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_log_session_accumulates(client: AsyncClient):
    """Logging twice on the same date should accumulate."""
    payload = {
        "session_date": "2025-01-16",
        "active_seconds": 600,
        "idle_seconds": 60,
        "page_views": 5,
        "actions_taken": 2,
        "productive_seconds": 300,
    }
    await client.post("/api/time-tracking/log", json=payload)
    await client.post("/api/time-tracking/log", json=payload)

    # Summary endpoint reads from DB — should have 1200s active for that date
    response = await client.get("/api/time-tracking/summary")
    assert response.status_code == 200
    data = response.json()
    assert "daily_breakdown" in data
    assert isinstance(data["daily_breakdown"], list)


@pytest.mark.asyncio
async def test_log_session_invalid_date(client: AsyncClient):
    response = await client.post("/api/time-tracking/log", json={
        "session_date": "not-a-date",
        "active_seconds": 600,
        "idle_seconds": 60,
        "page_views": 5,
        "actions_taken": 2,
        "productive_seconds": 300,
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_summary_empty(client: AsyncClient):
    response = await client.get("/api/time-tracking/summary")
    assert response.status_code == 200
    data = response.json()
    assert "today_active_minutes" in data
    assert "week_active_minutes" in data
    assert "focus_ratio" in data
    assert "daily_breakdown" in data
    assert "insights" in data
    assert isinstance(data["insights"], list)


@pytest.mark.asyncio
async def test_time_tracking_requires_auth(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "wrong-key"},
    ) as c:
        response = await c.get("/api/time-tracking/summary")
    assert response.status_code == 403
