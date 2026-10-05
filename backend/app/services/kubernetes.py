"""
Read-only Kubernetes API client.

When the app runs inside a Pod, Kubernetes mounts a ServiceAccount token at
/var/run/secrets/kubernetes.io/serviceaccount. We use it to read our own
Deployment, Pods, Service and Events (permissions granted in k8s/rbac.yaml),
so the dashboard reflects real cluster state — e.g. `kubectl scale` from 2 to 3
replicas shows up live.

Outside a cluster (local dev / docker run) we report "local" mode honestly.
"""
import asyncio
import os
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import (
    K8S_APP_LABEL,
    K8S_CONFIGMAP_NAME,
    K8S_DEPLOYMENT_NAME,
    K8S_SERVICE_NAME,
    NODE_NAME,
    POD_NAME,
    POD_NAMESPACE,
)
from app.services.cache import cached

SA_DIR = os.getenv("K8S_SA_DIR", "/var/run/secrets/kubernetes.io/serviceaccount")


def in_cluster() -> bool:
    return bool(os.getenv("KUBERNETES_SERVICE_HOST")) and os.path.exists(f"{SA_DIR}/token")


def _namespace() -> str:
    try:
        with open(f"{SA_DIR}/namespace") as f:
            return f.read().strip()
    except OSError:
        return POD_NAMESPACE


async def _get(client: httpx.AsyncClient, path: str) -> Dict[str, Any]:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


def _age(timestamp: Optional[str]) -> Optional[float]:
    if not timestamp:
        return None
    started = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return round((datetime.now(timezone.utc) - started).total_seconds(), 1)


def _pod_summary(pod: Dict[str, Any]) -> Dict[str, Any]:
    meta, spec, status = pod["metadata"], pod.get("spec", {}), pod.get("status", {})
    containers = status.get("containerStatuses", []) or []
    phase = status.get("phase", "Unknown")

    # Surface the same reason `kubectl get pods` shows (CrashLoopBackOff, ImagePullBackOff, ...)
    display = phase
    for c in containers:
        waiting = (c.get("state") or {}).get("waiting")
        if waiting and waiting.get("reason"):
            display = waiting["reason"]
            break
    if meta.get("deletionTimestamp"):
        display = "Terminating"

    return {
        "name": meta["name"],
        "status": display,
        "phase": phase,
        "ready": bool(containers) and all(c.get("ready") for c in containers),
        "restarts": sum(c.get("restartCount", 0) for c in containers),
        "node": spec.get("nodeName", "-"),
        "ip": status.get("podIP", "-"),
        "image": (spec.get("containers") or [{}])[0].get("image", "-"),
        "age_seconds": _age(status.get("startTime")),
        "is_current": meta["name"] == POD_NAME,
    }


def _event_summary(event: Dict[str, Any]) -> Dict[str, Any]:
    ts = (
        event.get("lastTimestamp")
        or event.get("eventTime")
        or event.get("metadata", {}).get("creationTimestamp")
        or ""
    )
    obj = event.get("involvedObject", {})
    return {
        "type": "kubernetes",
        "severity": "warning" if event.get("type") == "Warning" else "info",
        "reason": event.get("reason", ""),
        "object": f"{obj.get('kind', '')}/{obj.get('name', '')}",
        "message": event.get("message", ""),
        "count": event.get("count", 1),
        "timestamp": ts.replace("+00:00", "Z") if ts else "",
    }


async def _fetch_cluster() -> Dict[str, Any]:
    ns = _namespace()
    with open(f"{SA_DIR}/token") as f:
        token = f.read().strip()
    ctx = ssl.create_default_context(cafile=f"{SA_DIR}/ca.crt")
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.getenv("KUBERNETES_SERVICE_PORT", "443")

    async with httpx.AsyncClient(
        base_url=f"https://{host}:{port}",
        headers={"Authorization": f"Bearer {token}"},
        verify=ctx,
        timeout=3.0,
    ) as client:
        deployment, pods, service, events = await asyncio.gather(
            _get(client, f"/apis/apps/v1/namespaces/{ns}/deployments/{K8S_DEPLOYMENT_NAME}"),
            _get(client, f"/api/v1/namespaces/{ns}/pods?labelSelector={K8S_APP_LABEL}"),
            _get(client, f"/api/v1/namespaces/{ns}/services/{K8S_SERVICE_NAME}"),
            _get(client, f"/api/v1/namespaces/{ns}/events"),
            return_exceptions=True,
        )
        slices = await asyncio.gather(
            _get(
                client,
                f"/apis/discovery.k8s.io/v1/namespaces/{ns}/endpointslices"
                f"?labelSelector=kubernetes.io/service-name={K8S_SERVICE_NAME}",
            ),
            return_exceptions=True,
        )

    errors = [str(r) for r in (deployment, pods, service, events) if isinstance(r, Exception)]

    dep_info: Dict[str, Any] = {"name": K8S_DEPLOYMENT_NAME, "status": "Unknown"}
    if isinstance(deployment, dict):
        spec, st = deployment.get("spec", {}), deployment.get("status", {})
        conditions = {c["type"]: c for c in st.get("conditions", [])}
        available = conditions.get("Available", {}).get("status") == "True"
        progressing = conditions.get("Progressing", {})
        desired = spec.get("replicas", 0)
        ready = st.get("readyReplicas", 0)
        dep_info = {
            "name": K8S_DEPLOYMENT_NAME,
            "replicas_desired": desired,
            "replicas_available": st.get("availableReplicas", 0),
            "replicas_ready": ready,
            "replicas_updated": st.get("updatedReplicas", 0),
            "status": "Available" if available and ready >= desired else (
                "Progressing" if progressing.get("status") == "True" else "Degraded"
            ),
            "strategy": spec.get("strategy", {}).get("type", "RollingUpdate"),
            "image": spec.get("template", {}).get("spec", {}).get("containers", [{}])[0].get("image"),
            "generation": deployment.get("metadata", {}).get("generation"),
            "progress_message": progressing.get("message", ""),
        }

    pod_list: List[Dict[str, Any]] = []
    if isinstance(pods, dict):
        pod_list = sorted((_pod_summary(p) for p in pods.get("items", [])), key=lambda p: p["name"])

    svc_info: Dict[str, Any] = {"name": K8S_SERVICE_NAME, "status": "Unknown"}
    if isinstance(service, dict):
        ports = service.get("spec", {}).get("ports", [{}])
        ready_addresses = 0
        if isinstance(slices[0], dict):
            for endpoint_slice in slices[0].get("items", []):
                for ep in endpoint_slice.get("endpoints", []) or []:
                    if (ep.get("conditions") or {}).get("ready", True):
                        ready_addresses += 1
        svc_info = {
            "name": K8S_SERVICE_NAME,
            "type": service.get("spec", {}).get("type"),
            "cluster_ip": service.get("spec", {}).get("clusterIP"),
            "port": ports[0].get("port"),
            "target_port": ports[0].get("targetPort"),
            "node_port": ports[0].get("nodePort"),
            "endpoints": ready_addresses,
            "status": "Active" if ready_addresses > 0 else "No endpoints",
        }

    event_list: List[Dict[str, Any]] = []
    if isinstance(events, dict):
        event_list = [_event_summary(e) for e in events.get("items", [])]
        event_list.sort(key=lambda e: e["timestamp"], reverse=True)

    return {
        "mode": "kubernetes",
        "connected": not errors,
        "errors": errors,
        "namespace": ns,
        "deployment": dep_info,
        "pods": pod_list,
        "service": svc_info,
        "events": event_list[:30],
        "config_map": K8S_CONFIGMAP_NAME,
        "served_by": POD_NAME,
        "node": NODE_NAME,
    }


def _local_snapshot() -> Dict[str, Any]:
    return {
        "mode": "local",
        "connected": False,
        "errors": [],
        "namespace": "-",
        "deployment": {
            "name": K8S_DEPLOYMENT_NAME,
            "replicas_desired": 1,
            "replicas_available": 1,
            "replicas_ready": 1,
            "replicas_updated": 1,
            "status": "Local process",
            "strategy": "-",
            "image": None,
        },
        "pods": [{
            "name": POD_NAME,
            "status": "Running",
            "phase": "Running",
            "ready": True,
            "restarts": 0,
            "node": NODE_NAME,
            "ip": "127.0.0.1",
            "image": "-",
            "age_seconds": None,
            "is_current": True,
        }],
        "service": {"name": K8S_SERVICE_NAME, "type": "-", "status": "Not deployed", "endpoints": 0},
        "events": [],
        "config_map": K8S_CONFIGMAP_NAME,
        "served_by": POD_NAME,
        "node": NODE_NAME,
    }


async def get_cluster_snapshot() -> Dict[str, Any]:
    if not in_cluster():
        return _local_snapshot()

    async def produce() -> Dict[str, Any]:
        try:
            return await _fetch_cluster()
        except Exception as exc:  # API unreachable, RBAC missing, ...
            snap = _local_snapshot()
            snap.update(mode="kubernetes", connected=False, errors=[str(exc)])
            snap["deployment"]["status"] = "Unknown"
            return snap

    return await cached("k8s", 3.0, produce)
