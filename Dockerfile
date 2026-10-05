# ============================================================================
# DevOps Pulse — multi-stage Docker build
#
#   Stage 1 (frontend-build): Node builds the React/Vite dashboard -> /frontend/dist
#   Stage 2 (runtime):        Python runs FastAPI and serves the built dashboard
#
# Build:  docker build -t devops-pulse:1.0.0 .
# Run:    docker run -d -p 8000:8000 --name devops-pulse devops-pulse:1.0.0
# ============================================================================

# ---------- Stage 1: build the React frontend ----------
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Copy only the dependency manifests first so `npm ci` is cached between builds
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.11-slim AS runtime

# Build metadata injected by Jenkins (docker build --build-arg ...)
ARG APP_VERSION=1.0.0
ARG BUILD_NUMBER=local
ARG GIT_COMMIT=unknown
ARG BUILD_TIME=""
ARG IMAGE_NAME=devops-pulse:local

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    BUILD_NUMBER=${BUILD_NUMBER} \
    GIT_COMMIT=${GIT_COMMIT} \
    BUILD_TIME=${BUILD_TIME} \
    IMAGE_NAME=${IMAGE_NAME} \
    STATIC_DIR=/app/static

LABEL org.opencontainers.image.title="devops-pulse" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend-build /frontend/dist ./static

# Run as an unprivileged user
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
