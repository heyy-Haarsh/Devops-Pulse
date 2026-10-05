"""
Prometheus middleware — automatically records metrics for every HTTP request.
Runs as a Starlette middleware layer wrapping every request/response cycle.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import (
    http_requests_total,
    http_errors_total,
    http_request_duration_seconds,
    active_requests,
)


def _endpoint_label(request: Request, status_code: int) -> str:
    """Use the route template (e.g. /api/status) instead of the raw URL so that
    static assets and random 404 paths don't explode label cardinality."""
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    if request.url.path.startswith("/assets/"):
        return "/assets"
    return "unmatched" if status_code == 404 else request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record Prometheus metrics for every incoming HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip /metrics itself to avoid recursive counting
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        active_requests.inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            status_code = str(response.status_code)
            endpoint = _endpoint_label(request, response.status_code)

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            if response.status_code >= 400:
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                ).inc()

            return response

        except Exception as exc:
            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                status_code="500",
            ).inc()
            raise exc

        finally:
            active_requests.dec()
