"""
Health endpoint tests.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint returns application info."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DevOps Pulse"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_returns_200():
    """Health check returns HTTP 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_status_is_healthy():
    """Health check reports status=healthy."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_contains_required_fields():
    """Health response contains all required fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    for field in ["status", "version", "name", "environment", "uptime_seconds", "timestamp"]:
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_health_uptime_is_non_negative():
    """Uptime should be a non-negative number."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.json()["uptime_seconds"] >= 0
