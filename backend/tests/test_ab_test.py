"""
test_ab_test.py — Integration tests for A/B testing endpoints
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


@pytest.fixture
def ab_record_payload() -> dict:
    return {
        "topic_hash": "abc123ef",
        "style": "technical",
        "tone": "professional",
        "persona": "senior_engineer",
        "variation_index": 0,
        "engagement_prediction": 7,
    }


async def test_record_ab_selection(client: AsyncClient, ab_record_payload: dict):
    resp = await client.post("/api/ab-test/record", json=ab_record_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["style"] == ab_record_payload["style"]
    assert data["variation_index"] == 0
    assert "id" in data


async def test_update_actuals(client: AsyncClient, ab_record_payload: dict):
    create_resp = await client.post("/api/ab-test/record", json=ab_record_payload)
    record_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/ab-test/record/{record_id}/actuals",
        json={"actual_reactions": 80, "actual_comments": 15},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["actual_reactions"] == 80
    assert data["actual_comments"] == 15


async def test_update_actuals_nonexistent(client: AsyncClient):
    resp = await client.patch(
        "/api/ab-test/record/00000000-0000-0000-0000-000000000000/actuals",
        json={"actual_impressions": 100},
    )
    assert resp.status_code == 404


async def test_get_summary(client: AsyncClient, ab_record_payload: dict):
    # Create at least one record
    await client.post("/api/ab-test/record", json=ab_record_payload)

    resp = await client.get("/api/ab-test/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert isinstance(body["summary"], list)


async def test_get_summary_with_limit(client: AsyncClient, ab_record_payload: dict):
    for _ in range(3):
        await client.post("/api/ab-test/record", json=ab_record_payload)

    resp = await client.get("/api/ab-test/summary", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["summary"]) <= 2
