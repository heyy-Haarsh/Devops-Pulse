"""
Status, metrics summary, deployment, Kubernetes, events, and monitoring endpoints.
All data is returned as JSON for consumption by the React frontend.

Data sources (in order of preference):
  - Kubernetes API (in-cluster ServiceAccount)  -> pods, replicas, service, events
  - Prometheus HTTP API (PromQL)                -> cluster-wide request/error/latency
  - This process's prometheus_client registry   -> fallback when running locally
"""
from typing import Any, Dict, List

from fastapi import APIRouter
from app.config import (
    APP_VERSION,
    BUILD_NUMBER,
    BUILD_TIME,
    ENVIRONMENT,
    GIT_COMMIT,
    GRAFANA_PUBLIC_URL,
    IMAGE_NAME,
    NODE_NAME,
    POD_NAME,
    PROMETHEUS_PUBLIC_URL,
    START_TIME,
    utcnow,
)
from app.metrics import deployment_events_total, replica_count, system_health_score
from app.services.kubernetes import get_cluster_snapshot
from app.services.local_stats import local_summary
from app.services.monitoring import get_monitoring_status, query_summary

router = APIRouter(prefix="/api", tags=["Status"])

# ─── In-memory application event store ───────────────────────────────────────

_events: List[Dict[str, Any]] = [
    {
        "id": 1,
        "type": "deployment",
        "severity": "success",
        "message": (
            f"DevOps Pulse v{APP_VERSION} started on {POD_NAME} "
            f"(image {IMAGE_NAME}, build #{BUILD_NUMBER}, commit {GIT_COMMIT[:7]})"
        ),
        "timestamp": START_TIME.isoformat() + "Z",
    },
]
_event_id_counter = 2


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _format_uptime(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _uptime() -> float:
    return (utcnow() - START_TIME).total_seconds()


def _diagnostics(k8s: Dict[str, Any], mon: Dict[str, Any]) -> List[Dict[str, str]]:
    """Checklist shown in the 'System Diagnostics' panel. status: ok | warn | error | off"""
    checks: List[Dict[str, str]] = [
        {"name": "Backend API", "status": "ok", "detail": f"Serving from {POD_NAME}"},
    ]

    if k8s["mode"] == "local":
        checks.append({"name": "Kubernetes API", "status": "off", "detail": "Not running in a cluster"})
    else:
        dep, svc = k8s["deployment"], k8s["service"]
        pods = k8s["pods"]
        ready = sum(1 for p in pods if p["ready"])
        desired = dep.get("replicas_desired", len(pods))
        checks.append({
            "name": "Kubernetes API",
            "status": "ok" if k8s["connected"] else "error",
            "detail": "Connected" if k8s["connected"] else "; ".join(k8s["errors"])[:120],
        })
        checks.append({
            "name": "Application Pods",
            "status": "ok" if desired and ready >= desired else ("warn" if ready else "error"),
            "detail": f"{ready}/{desired} Running & Ready",
        })
        checks.append({
            "name": "Service",
            "status": "ok" if svc.get("endpoints", 0) > 0 else "error",
            "detail": f"{svc.get('type', '?')} · {svc.get('endpoints', 0)} endpoints",
        })

    prom = mon["prometheus"]
    if prom["status"] == "not_configured":
        checks.append({"name": "Prometheus", "status": "off", "detail": "PROMETHEUS_URL not set"})
    elif prom["status"] != "healthy":
        checks.append({"name": "Prometheus", "status": "error", "detail": "Unreachable"})
    else:
        up, total = prom.get("targets_up", 0), prom.get("targets_total", 0)
        firing = [a for a in prom.get("alerts", []) if a["state"] == "firing"]
        status = "ok" if total and up == total and not firing else ("warn" if up else "error")
        detail = f"Scraping {up}/{total} targets UP"
        if firing:
            detail += f" · {len(firing)} alert(s) firing"
        checks.append({"name": "Prometheus", "status": status, "detail": detail})

    graf = mon["grafana"]
    if graf["status"] == "not_configured":
        checks.append({"name": "Grafana", "status": "off", "detail": "GRAFANA_URL not set"})
    elif graf["status"] != "healthy":
        checks.append({"name": "Grafana", "status": "error", "detail": "Unreachable"})
    else:
        ds_ok = graf.get("datasource_ok", False)
        checks.append({
            "name": "Grafana",
            "status": "ok" if ds_ok else "warn",
            "detail": f"Connected · {graf.get('dashboards', 0)} dashboard(s)"
            if ds_ok else "Up, but Prometheus datasource query failed",
        })
    return checks


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Overall system status plus a diagnostics checklist across the whole stack."""
    k8s = await get_cluster_snapshot()
    mon = await get_monitoring_status()
    checks = _diagnostics(k8s, mon)

    active = [c for c in checks if c["status"] != "off"]
    score = round(100 * sum(1 for c in active if c["status"] == "ok") / len(active)) if active else 100
    system_health_score.set(score)
    overall = "healthy" if score == 100 else ("degraded" if score >= 50 else "critical")

    return {
        "status": "healthy",  # this API process itself is up
        "overall": overall,
        "health_score": score,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "uptime_seconds": round(_uptime(), 2),
        "timestamp": utcnow().isoformat() + "Z",
        "served_by": POD_NAME,
        "services": {c["name"]: c["status"] for c in checks},
        "diagnostics": checks,
    }


@router.get("/metrics-summary")
async def get_metrics_summary():
    """Key application metrics. Cluster-wide via Prometheus when available,
    otherwise computed from this process's own counters."""
    uptime = _uptime()
    prom = await query_summary()

    if prom and prom.get("instances_up") is not None:
        rate = prom["request_rate"] or 0.0
        errors = prom["error_rate"] or 0.0
        count = prom["latency_count"] or 0.0
        avg_latency = (prom["latency_sum"] or 0.0) / count if count else 0.0
        data = {
            "source": "prometheus",
            "request_rate": rate,
            "error_rate": errors,
            "avg_latency_s": avg_latency,
            "p95_latency_s": prom["p95"] or 0.0,
            "active_requests": prom["active_requests"] or 0,
            "total_requests": prom["total_requests"] or 0,
            "total_errors": prom["total_errors"] or 0,
            "instances_up": int(prom["instances_up"] or 0),
        }
    else:
        local = local_summary()
        data = {"source": "local", "p95_latency_s": None, "instances_up": 1, **local}

    rate = data["request_rate"]
    return {
        "source": data["source"],
        "request_rate_per_second": round(rate, 2),
        "average_latency_ms": round(data["avg_latency_s"] * 1000, 2),
        "p95_latency_ms": round(data["p95_latency_s"] * 1000, 2) if data["p95_latency_s"] is not None else None,
        "error_rate_percent": round(100 * data["error_rate"] / rate, 2) if rate else 0.0,
        "active_requests": int(data["active_requests"]),
        "uptime_seconds": round(uptime, 2),
        "uptime_human": _format_uptime(uptime),
        "total_requests": int(data["total_requests"]),
        "total_errors": int(data["total_errors"]),
        "instances_up": data["instances_up"],
        "version": APP_VERSION,
        "served_by": POD_NAME,
        "timestamp": utcnow().isoformat() + "Z",
    }


@router.get("/deployment")
async def get_deployment_info():
    """Deployment information — build metadata from Jenkins, image, replicas, strategy."""
    k8s = await get_cluster_snapshot()
    dep = k8s["deployment"]
    replica_count.set(dep.get("replicas_desired", 1))
    return {
        "app_name": "devops-pulse",
        "version": APP_VERSION,
        "build_number": BUILD_NUMBER,
        "git_commit": GIT_COMMIT,
        "build_time": BUILD_TIME or None,
        "image": dep.get("image") or IMAGE_NAME,
        "status": "Running" if dep.get("status") in ("Available", "Local process") else dep.get("status"),
        "replicas": {
            "desired": dep.get("replicas_desired", 1),
            "available": dep.get("replicas_available", 0),
            "ready": dep.get("replicas_ready", 0),
            "updated": dep.get("replicas_updated", 0),
        },
        "deployed_at": START_TIME.isoformat() + "Z",
        "environment": ENVIRONMENT,
        "strategy": dep.get("strategy", "-"),
        "namespace": k8s["namespace"],
        "mode": k8s["mode"],
    }


@router.get("/kubernetes")
async def get_kubernetes_info():
    """Kubernetes cluster information (namespace, deployment, pods, service)."""
    k8s = await get_cluster_snapshot()
    return {key: value for key, value in k8s.items() if key != "events"}


@router.get("/events")
async def get_events():
    """System events feed — application events merged with Kubernetes events."""
    k8s = await get_cluster_snapshot()
    merged = list(_events) + k8s.get("events", [])
    merged.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return {"events": merged[:25], "total": len(merged)}


@router.post("/events")
async def create_event(event: Dict[str, Any]):
    """Record a new system event."""
    global _event_id_counter
    new_event = {
        "id": _event_id_counter,
        "type": event.get("type", "info"),
        "severity": event.get("severity", "info"),
        "message": event.get("message", ""),
        "timestamp": utcnow().isoformat() + "Z",
    }
    _events.append(new_event)
    _event_id_counter += 1
    deployment_events_total.labels(event_type=event.get("type", "info")).inc()
    return new_event


@router.get("/monitoring")
async def get_monitoring_info():
    """Monitoring stack status (Prometheus targets/alerts + Grafana connectivity)."""
    mon = await get_monitoring_status()
    return {
        "prometheus": {**mon["prometheus"], "url": PROMETHEUS_PUBLIC_URL},
        "grafana": {**mon["grafana"], "url": GRAFANA_PUBLIC_URL},
        "node": NODE_NAME,
    }
