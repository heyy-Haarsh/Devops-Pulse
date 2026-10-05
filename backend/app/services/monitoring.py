"""
Prometheus + Grafana integration.

The dashboard asks Prometheus for cluster-wide numbers (all replicas combined)
using the same PromQL that the Grafana dashboard uses. If Prometheus is not
configured/reachable we fall back to this process's own counters.
"""
import asyncio
import math
from typing import Any, Dict, List, Optional

import httpx

from app.config import GRAFANA_URL, PROMETHEUS_JOB, PROMETHEUS_URL
from app.services.cache import cached

JOB = PROMETHEUS_JOB

# PromQL used by /api/metrics-summary (mirrors the Grafana panels)
QUERIES = {
    "request_rate": f'sum(rate(http_requests_total{{job="{JOB}"}}[1m]))',
    "error_rate": f'sum(rate(http_errors_total{{job="{JOB}"}}[1m]))',
    "latency_sum": f'sum(rate(http_request_duration_seconds_sum{{job="{JOB}"}}[1m]))',
    "latency_count": f'sum(rate(http_request_duration_seconds_count{{job="{JOB}"}}[1m]))',
    "p95": f'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{{job="{JOB}"}}[1m])))',
    "active_requests": f'sum(active_requests{{job="{JOB}"}})',
    "total_requests": f'sum(http_requests_total{{job="{JOB}"}})',
    "total_errors": f'sum(http_errors_total{{job="{JOB}"}})',
    "instances_up": f'sum(up{{job="{JOB}"}})',
}


def _to_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


async def _instant(client: httpx.AsyncClient, query: str) -> Optional[float]:
    r = await client.get("/api/v1/query", params={"query": query})
    r.raise_for_status()
    result = r.json().get("data", {}).get("result", [])
    if not result:
        return None
    return _to_float(result[0]["value"][1])


async def query_summary() -> Optional[Dict[str, Optional[float]]]:
    """Run all summary queries against Prometheus. None if unavailable."""
    if not PROMETHEUS_URL:
        return None

    async def produce():
        try:
            async with httpx.AsyncClient(base_url=PROMETHEUS_URL, timeout=2.0) as client:
                values = await asyncio.gather(*(_instant(client, q) for q in QUERIES.values()))
            return dict(zip(QUERIES.keys(), values))
        except Exception:
            return None

    return await cached("prom-summary", 3.0, produce)


async def _prometheus_status(client: httpx.AsyncClient) -> Dict[str, Any]:
    info: Dict[str, Any] = {"configured": bool(PROMETHEUS_URL), "status": "not_configured"}
    if not PROMETHEUS_URL:
        return info
    try:
        targets_resp, alerts_resp = await asyncio.gather(
            client.get(f"{PROMETHEUS_URL}/api/v1/targets", params={"state": "active"}),
            client.get(f"{PROMETHEUS_URL}/api/v1/alerts"),
        )
        targets_resp.raise_for_status()
        active = targets_resp.json()["data"]["activeTargets"]
        app_targets = [t for t in active if t.get("labels", {}).get("job") == JOB]
        up = [t for t in app_targets if t.get("health") == "up"]

        alerts: List[Dict[str, Any]] = []
        if alerts_resp.status_code == 200:
            for a in alerts_resp.json()["data"]["alerts"]:
                alerts.append({
                    "name": a["labels"].get("alertname"),
                    "state": a.get("state"),
                    "severity": a["labels"].get("severity", "warning"),
                    "summary": a.get("annotations", {}).get("summary", ""),
                    "active_at": a.get("activeAt"),
                })

        info.update(
            status="healthy",
            targets_up=len(up),
            targets_total=len(app_targets),
            targets=[{
                "instance": t["labels"].get("instance"),
                "pod": t["labels"].get("pod"),
                "health": t.get("health"),
                "last_scrape": t.get("lastScrape"),
                "last_error": t.get("lastError", ""),
                "scrape_url": t.get("scrapeUrl"),
            } for t in app_targets],
            scrape_interval=app_targets[0].get("scrapeInterval") if app_targets else None,
            alerts=alerts,
        )
    except Exception as exc:
        info.update(status="unreachable", error=str(exc))
    return info


async def _grafana_status(client: httpx.AsyncClient) -> Dict[str, Any]:
    info: Dict[str, Any] = {"configured": bool(GRAFANA_URL), "status": "not_configured"}
    if not GRAFANA_URL:
        return info
    try:
        health = await client.get(f"{GRAFANA_URL}/api/health")
        health.raise_for_status()
        info.update(status="healthy", version=health.json().get("version"))

        search = await client.get(f"{GRAFANA_URL}/api/search", params={"type": "dash-db"})
        if search.status_code == 200:
            info["dashboards"] = len(search.json())

        # End-to-end check: ask Grafana to run a PromQL query through its datasource
        probe = await client.post(
            f"{GRAFANA_URL}/api/ds/query",
            json={
                "queries": [{
                    "refId": "A",
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": f'up{{job="{JOB}"}}',
                    "instant": True,
                }],
                "from": "now-5m",
                "to": "now",
            },
        )
        info["datasource_ok"] = probe.status_code == 200 and "error" not in probe.json().get(
            "results", {}).get("A", {})
    except Exception as exc:
        info.update(status="unreachable", error=str(exc))
    return info


async def get_monitoring_status() -> Dict[str, Any]:
    async def produce():
        async with httpx.AsyncClient(timeout=2.0) as client:
            prom, graf = await asyncio.gather(_prometheus_status(client), _grafana_status(client))
        return {"prometheus": prom, "grafana": graf}

    return await cached("monitoring", 3.0, produce)
