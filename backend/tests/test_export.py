"""
test_export.py — Integration tests for CSV export endpoints
"""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_export_drafts_csv(client: AsyncClient):
    resp = await client.get("/api/export/drafts")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")
    # CSV should have a header row at minimum
    assert "id" in resp.text.lower() or resp.text == "" or resp.text.startswith("id,")


async def test_export_engagement_csv(client: AsyncClient):
    resp = await client.get("/api/export/engagement")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_export_ab_tests_csv(client: AsyncClient):
    resp = await client.get("/api/export/ab-tests")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")


async def test_export_drafts_with_limit(client: AsyncClient):
    resp = await client.get("/api/export/drafts", params={"limit": 10})
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
