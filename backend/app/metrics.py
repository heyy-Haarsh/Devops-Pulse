"""
Prometheus metrics definitions for DevOps Pulse.

Metric types demonstrated:
  Counter   - monotonically increasing (requests, errors)
  Gauge     - can go up and down (active_requests, uptime)
  Histogram - distribution of values (latency)
  Info      - static key-value info (app version, environment)
"""
from prometheus_client import Counter, Gauge, Histogram, Info

# ─── Counters ────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests received",
    ["method", "endpoint", "status_code"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total number of HTTP errors (4xx and 5xx responses)",
    ["method", "endpoint", "status_code"],
)

deployment_events_total = Counter(
    "deployment_events_total",
    "Total number of deployment events recorded",
    ["event_type"],
)

# ─── Gauges ──────────────────────────────────────────────────────────────────

active_requests = Gauge(
    "active_requests",
    "Number of HTTP requests currently being processed",
)

app_uptime_seconds = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds since last start",
)

replica_count = Gauge(
    "replica_count",
    "Current number of configured Kubernetes replicas",
)

system_health_score = Gauge(
    "system_health_score",
    "Overall system health score from 0 to 100",
)

# ─── Histograms ───────────────────────────────────────────────────────────────

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ─── Info ────────────────────────────────────────────────────────────────────

app_info = Info(
    "app",
    "DevOps Pulse application build and runtime information",
)


def init_route_metrics(routes) -> None:
    """Create every endpoint's request/error series at 0 on startup.

    Prometheus' rate() only sees an increase between two scrapes of an existing
    series. Without this, the first burst of e.g. HTTP 500s creates a brand-new
    series that already starts at N, and the error-rate graphs/alerts stay at 0.
    """
    for route in routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods or path == "/metrics":
            continue
        for method in methods - {"HEAD", "OPTIONS"}:
            http_requests_total.labels(method=method, endpoint=path, status_code="200")
            http_requests_total.labels(method=method, endpoint=path, status_code="500")
            http_errors_total.labels(method=method, endpoint=path, status_code="500")
    http_requests_total.labels(method="GET", endpoint="unmatched", status_code="404")
    http_errors_total.labels(method="GET", endpoint="unmatched", status_code="404")


def init_metrics(version: str, environment: str) -> None:
    """Initialize static metric values on application startup."""
    app_info.info({
        "version": version,
        "environment": environment,
        "name": "devops-pulse",
    })
    replica_count.set(1)  # refreshed from the Kubernetes API by /api/deployment
    system_health_score.set(100)
    deployment_events_total.labels(event_type="startup").inc()
