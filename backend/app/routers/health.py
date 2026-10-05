"""
Health check and root endpoints.
"""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import APP_VERSION, APP_NAME, ENVIRONMENT, START_TIME, STATIC_DIR, utcnow

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    name: str
    environment: str
    uptime_seconds: float
    timestamp: str


@router.get("/", tags=["Root"])
async def root(request: Request):
    """Root endpoint — browsers get the React dashboard (when built),
    API clients get basic application info as JSON."""
    index = STATIC_DIR / "index.html"
    if "text/html" in request.headers.get("accept", "") and index.is_file():
        return FileResponse(index)
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint used by Docker HEALTHCHECK, Kubernetes probes,
    and Prometheus target scraping."""
    uptime = (utcnow() - START_TIME).total_seconds()
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        name=APP_NAME,
        environment=ENVIRONMENT,
        uptime_seconds=round(uptime, 2),
        timestamp=utcnow().isoformat() + "Z",
    )
