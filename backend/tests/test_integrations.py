"""
Tests for real-data behaviour: local fallback mode, Kubernetes parsing,
demo traffic endpoints and Prometheus label hygiene.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.kubernetes import _event_summary, _pod_summary


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_kubernetes_reports_local_mode_outside_cluster():
    async with client() as c:
        data = (await c.get("/api/kubernetes")).json()
    assert data["mode"] == "local"
    assert data["pods"][0]["status"] == "Running"


@pytest.mark.asyncio
async def test_metrics_summary_uses_local_counters_without_prometheus():
    async with client() as c:
        for _ in range(5):
            await c.get("/health")
        data = (await c.get("/api/metrics-summary")).json()
    assert data["source"] == "local"
    assert data["total_requests"] >= 5
    assert data["error_rate_percent"] >= 0


@pytest.mark.asyncio
async def test_status_contains_diagnostics_checklist():
    async with client() as c:
        data = (await c.get("/api/status")).json()
    names = [d["name"] for d in data["diagnostics"]]
    assert "Backend API" in names
    assert "Prometheus" in names
    assert data["overall"] in ("healthy", "degraded", "critical")
    assert 0 <= data["health_score"] <= 100


@pytest.mark.asyncio
async def test_deployment_exposes_build_metadata():
    async with client() as c:
        data = (await c.get("/api/deployment")).json()
    for field in ["build_number", "git_commit", "image", "mode"]:
        assert field in data


@pytest.mark.asyncio
async def test_demo_error_endpoint_is_counted_as_error():
    async with client() as c:
        response = await c.get("/api/demo/error")
        metrics = (await c.get("/metrics")).text
    assert response.status_code == 500
    assert 'http_errors_total{endpoint="/api/demo/error",method="GET",status_code="500"}' in metrics


@pytest.mark.asyncio
async def test_demo_slow_endpoint_is_bounded():
    async with client() as c:
        assert (await c.get("/api/demo/slow?ms=10")).status_code == 200
        assert (await c.get("/api/demo/slow?ms=999999")).status_code == 422


@pytest.mark.asyncio
async def test_unknown_paths_do_not_create_new_metric_labels():
    async with client() as c:
        await c.get("/some/random/path-123")
        metrics = (await c.get("/metrics")).text
    assert "path-123" not in metrics
    assert 'endpoint="unmatched"' in metrics


@pytest.mark.asyncio
async def test_root_returns_json_for_api_clients():
    async with client() as c:
        response = await c.get("/", headers={"accept": "application/json"})
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_route_metrics_are_initialised_at_zero():
    """Error series must exist (at 0) before the first error, otherwise
    Prometheus rate() cannot detect the first burst of errors."""
    from app.metrics import init_route_metrics
    init_route_metrics(app.routes)
    async with client() as c:
        metrics = (await c.get("/metrics")).text
    assert 'http_errors_total{endpoint="/api/demo/ok",method="GET",status_code="500"} 0.0' in metrics
    assert 'http_requests_total{endpoint="/api/status",method="GET",status_code="200"}' in metrics


def test_pod_summary_surfaces_waiting_reason():
    pod = {
        "metadata": {"name": "devops-pulse-abc"},
        "spec": {"nodeName": "minikube", "containers": [{"image": "devops-pulse:7"}]},
        "status": {
            "phase": "Running",
            "podIP": "10.244.0.5",
            "containerStatuses": [{
                "ready": False,
                "restartCount": 4,
                "state": {"waiting": {"reason": "CrashLoopBackOff"}},
            }],
        },
    }
    summary = _pod_summary(pod)
    assert summary["status"] == "CrashLoopBackOff"
    assert summary["ready"] is False
    assert summary["restarts"] == 4
    assert summary["image"] == "devops-pulse:7"


def test_event_summary_maps_warning_severity():
    event = {
        "type": "Warning",
        "reason": "BackOff",
        "message": "Back-off restarting failed container",
        "involvedObject": {"kind": "Pod", "name": "devops-pulse-abc"},
        "lastTimestamp": "2026-01-01T00:00:00Z",
    }
    summary = _event_summary(event)
    assert summary["severity"] == "warning"
    assert summary["object"] == "Pod/devops-pulse-abc"
