"""
API endpoint tests — covers all /api/* routes.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_metrics_summary_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/metrics-summary")
    assert response.status_code == 200
    data = response.json()
    assert "request_rate_per_second" in data
    assert "average_latency_ms" in data
    assert "error_rate_percent" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_deployment_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/deployment")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "status" in data
    assert "replicas" in data
    assert data["replicas"]["desired"] >= 1


@pytest.mark.asyncio
async def test_kubernetes_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/kubernetes")
    assert response.status_code == 200
    data = response.json()
    assert "namespace" in data
    assert "deployment" in data
    assert "pods" in data
    assert "service" in data
    assert isinstance(data["pods"], list)
    assert len(data["pods"]) > 0


@pytest.mark.asyncio
async def test_events_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0


@pytest.mark.asyncio
async def test_monitoring_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/monitoring")
    assert response.status_code == 200
    data = response.json()
    assert "prometheus" in data
    assert "grafana" in data
