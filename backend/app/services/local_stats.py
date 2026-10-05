"""
Fallback statistics computed from this process's own prometheus_client
registry (used when Prometheus is not configured, e.g. local dev).
Rates are derived from snapshots taken over the last ~60 seconds.
"""
import time
from collections import deque
from typing import Deque, Dict, Tuple

from app.metrics import (
    active_requests,
    http_errors_total,
    http_request_duration_seconds,
    http_requests_total,
)

WINDOW_SECONDS = 60
_snapshots: Deque[Tuple[float, Dict[str, float]]] = deque(maxlen=200)


def _sum(metric, sample_name: str) -> float:
    return sum(
        s.value
        for family in metric.collect()
        for s in family.samples
        if s.name == sample_name
    )


def _totals() -> Dict[str, float]:
    return {
        "requests": _sum(http_requests_total, "http_requests_total"),
        "errors": _sum(http_errors_total, "http_errors_total"),
        "latency_sum": _sum(http_request_duration_seconds, "http_request_duration_seconds_sum"),
        "latency_count": _sum(http_request_duration_seconds, "http_request_duration_seconds_count"),
    }


def local_summary() -> Dict[str, float]:
    now = time.monotonic()
    current = _totals()
    _snapshots.append((now, current))
    while _snapshots and now - _snapshots[0][0] > WINDOW_SECONDS:
        _snapshots.popleft()

    t0, first = _snapshots[0]
    elapsed = now - t0
    if elapsed > 0:
        d = {k: current[k] - first[k] for k in current}
        request_rate = d["requests"] / elapsed
        error_rate = d["errors"] / elapsed
        avg_latency = d["latency_sum"] / d["latency_count"] if d["latency_count"] else 0.0
    else:
        request_rate = error_rate = 0.0
        count = current["latency_count"]
        avg_latency = current["latency_sum"] / count if count else 0.0

    return {
        "request_rate": request_rate,
        "error_rate": error_rate,
        "avg_latency_s": avg_latency,
        "active_requests": active_requests._value.get(),
        "total_requests": current["requests"],
        "total_errors": current["errors"],
    }
