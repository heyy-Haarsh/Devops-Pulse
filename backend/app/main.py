"""
DevOps Pulse — FastAPI Backend Entry Point

Pipeline: Git → Jenkins → Docker → Kubernetes → Prometheus → Grafana
Exposes REST APIs consumed by the React dashboard and a /metrics endpoint
scraped by Prometheus.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.config import (
    APP_VERSION, APP_NAME, ENVIRONMENT, CORS_ORIGINS, START_TIME, STATIC_DIR,
    BUILD_NUMBER, GIT_COMMIT, IMAGE_NAME, utcnow,
)
from app.metrics import init_metrics, init_route_metrics, app_uptime_seconds
from app.middleware import PrometheusMiddleware
from app.routers import demo, health, status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    init_metrics(version=APP_VERSION, environment=ENVIRONMENT)
    init_route_metrics(app.routes)
    print(
        f"[DevOps Pulse] Starting v{APP_VERSION} | env={ENVIRONMENT} | "
        f"image={IMAGE_NAME} | build={BUILD_NUMBER} | commit={GIT_COMMIT[:7]}",
        flush=True,
    )
    yield
    print("[DevOps Pulse] Shutting down")


app = FastAPI(
    title=APP_NAME,
    description="""
## DevOps Pulse — Backend API

Demonstrates the complete DevOps pipeline:
**Git → Jenkins → Docker → Kubernetes → Prometheus → Grafana**

### Endpoints
| Path | Description |
|------|-------------|
| `/` | Root info |
| `/health` | Liveness / readiness probe |
| `/api/status` | System status |
| `/api/metrics-summary` | Dashboard metrics |
| `/api/deployment` | Deployment info |
| `/api/kubernetes` | Kubernetes cluster info |
| `/api/events` | System events feed |
| `/api/monitoring` | Monitoring stack status |
| `/api/demo/*` | Traffic generator helpers (ok / error / slow) |
| `/metrics` | Prometheus scrape endpoint |
    """,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PrometheusMiddleware)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(status.router)
app.include_router(demo.router)

# Built React dashboard assets (present inside the Docker image)
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

# ─── Prometheus Metrics Endpoint ──────────────────────────────────────────────

@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics scrape endpoint — consumed by Prometheus every 10-15 s."""
    uptime = (utcnow() - START_TIME).total_seconds()
    app_uptime_seconds.set(uptime)
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
