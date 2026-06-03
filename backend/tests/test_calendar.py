"""
test_calendar.py — Integration tests for content calendar endpoints
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


@pytest.fixture
def scheduled_post_payload() -> dict:
    return {
        "title": "My next big post",
        "content": "Here is the draft content for my upcoming LinkedIn post about async Python.",
        "scheduled_for": "2099-06-01T09:00:00Z",
        "status": "scheduled",
    }


async def test_create_scheduled_post(client: AsyncClient, scheduled_post_payload: dict):
    resp = await client.post("/api/calendar", json=scheduled_post_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == scheduled_post_payload["title"]
    assert data["status"] == "scheduled"
    assert "id" in data


async def test_list_scheduled_posts(client: AsyncClient, scheduled_post_payload: dict):
    # Create one first
    await client.post("/api/calendar", json=scheduled_post_payload)

    resp = await client.get("/api/calendar")
    assert resp.status_code == 200
    body = resp.json()
    assert "posts" in body
    assert isinstance(body["posts"], list)
    assert len(body["posts"]) >= 1


async def test_list_filter_by_status(client: AsyncClient, scheduled_post_payload: dict):
    await client.post("/api/calendar", json=scheduled_post_payload)

    resp = await client.get("/api/calendar", params={"status": "scheduled"})
    assert resp.status_code == 200
    posts = resp.json()["posts"]
    assert all(p["status"] == "scheduled" for p in posts)


async def test_get_single_post(client: AsyncClient, scheduled_post_payload: dict):
    create_resp = await client.post("/api/calendar", json=scheduled_post_payload)
    post_id = create_resp.json()["id"]

    resp = await client.get(f"/api/calendar/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == post_id


async def test_get_nonexistent_post(client: AsyncClient):
    resp = await client.get("/api/calendar/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_update_post(client: AsyncClient, scheduled_post_payload: dict):
    create_resp = await client.post("/api/calendar", json=scheduled_post_payload)
    post_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/calendar/{post_id}", json={"status": "published"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


async def test_delete_post(client: AsyncClient, scheduled_post_payload: dict):
    create_resp = await client.post("/api/calendar", json=scheduled_post_payload)
    post_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/calendar/{post_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/calendar/{post_id}")
    assert get_resp.status_code == 404
