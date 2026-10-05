"""
Prometheus /metrics endpoint tests.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_metrics_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_content_type_is_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_contains_uptime():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert b"app_uptime_seconds" in response.content


@pytest.mark.asyncio
async def test_metrics_contains_app_info():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert b"app_info" in response.content


@pytest.mark.asyncio
async def test_metrics_contains_http_requests_after_traffic():
    """After hitting /health, http_requests_total should appear in /metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/health")
        response = await client.get("/metrics")
    assert b"http_requests_total" in response.content
