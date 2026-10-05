import os
import socket
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> datetime:
    """Naive UTC timestamp (datetime.utcnow() is deprecated since Python 3.12)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)



# Application version - update this to demonstrate CI/CD version bumps
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_NAME = "DevOps Pulse"
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# Build metadata — injected by Jenkins as Docker build args (see Dockerfile / Jenkinsfile)
BUILD_NUMBER = os.getenv("BUILD_NUMBER", "local")
GIT_COMMIT = os.getenv("GIT_COMMIT", "unknown")
BUILD_TIME = os.getenv("BUILD_TIME", "")
IMAGE_NAME = os.getenv("IMAGE_NAME", f"devops-pulse:{APP_VERSION}")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Kubernetes identity — injected through the Downward API in k8s/deployment.yaml
POD_NAME = os.getenv("POD_NAME", socket.gethostname())
POD_NAMESPACE = os.getenv("POD_NAMESPACE", "devops-pulse")
NODE_NAME = os.getenv("NODE_NAME", "localhost")
K8S_DEPLOYMENT_NAME = os.getenv("K8S_DEPLOYMENT_NAME", "devops-pulse")
K8S_SERVICE_NAME = os.getenv("K8S_SERVICE_NAME", "devops-pulse-service")
K8S_APP_LABEL = os.getenv("K8S_APP_LABEL", "app=devops-pulse")
K8S_CONFIGMAP_NAME = os.getenv("K8S_CONFIGMAP_NAME", "devops-pulse-config")

# Monitoring stack. Empty URL = integration disabled (e.g. plain local dev / tests).
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "").rstrip("/")
GRAFANA_URL = os.getenv("GRAFANA_URL", "").rstrip("/")
PROMETHEUS_JOB = os.getenv("PROMETHEUS_JOB", "devops-pulse")
# Browser-facing links shown in the dashboard (usually kubectl port-forward targets)
PROMETHEUS_PUBLIC_URL = os.getenv("PROMETHEUS_PUBLIC_URL", "http://localhost:9090")
GRAFANA_PUBLIC_URL = os.getenv("GRAFANA_PUBLIC_URL", "http://localhost:3001")

# Built React dashboard (copied here by the Dockerfile)
STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))

# Application start time (set at import time)
START_TIME = utcnow()
