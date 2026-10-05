# DevOps Pulse

**A DevOps monitoring and control dashboard that demonstrates a complete, integrated delivery pipeline:**

```
Git ──► Jenkins ──► Docker ──► Kubernetes ──► Prometheus ──► Grafana
```

DevOps Pulse is a React + FastAPI application that is *built* by Jenkins, *shipped* as a Docker image,
*deployed and scaled* on Kubernetes (Minikube), and *observed* by Prometheus and Grafana. The dashboard
itself reads live data back from every stage — the Git commit and Jenkins build number baked into the
image, the Pods and replicas from the Kubernetes API, and cluster-wide metrics from Prometheus — so the
output of each stage is visibly the input of the next.

---

## Table of contents

1. [Architecture](#architecture)
2. [Technology stack](#technology-stack)
3. [Project structure](#project-structure)
4. [Local development](#local-development)
5. [Docker](#docker)
6. [Kubernetes (Minikube)](#kubernetes-minikube)
7. [Prometheus](#prometheus)
8. [Grafana](#grafana)
9. [Jenkins CI/CD](#jenkins-cicd)
10. [Git workflow](#git-workflow)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)
13. [Useful commands](#useful-commands)
14. [Assessment demonstration flow](#assessment-demonstration-flow)

---

## Architecture

```
 Developer
    │  git push
    ▼
 ┌────────┐  poll every 2 min   ┌──────────────────────────────────────────────────────────┐
 │ GitHub │ ◄────────────────── │ Jenkins (Docker container on the "minikube" network)     │
 └────────┘     git clone       │  Checkout → Install → Test → Build Frontend              │
                                │  → Build Docker Image → Deploy to Kubernetes → Verify    │
                                └───────────┬──────────────────────────┬───────────────────┘
                     docker build           │                          │  kubectl apply / set image
                     (Minikube's daemon)    ▼                          ▼
                              ┌──────────────────────┐   ┌─────────────────────────────────────┐
                              │ Image                │   │ Minikube                            │
                              │ devops-pulse:<BUILD> │──►│  ns devops-pulse                    │
                              └──────────────────────┘   │   Deployment (2→3 replicas)         │
                                                         │   Pods :8000  /health  /metrics     │
                                                         │   Service NodePort 80 → 8000        │
                                                         │  ns monitoring                      │
                                                         │   Prometheus ──scrape /metrics──►Pods│
                                                         │   Grafana ──PromQL──► Prometheus     │
                                                         └─────────────────────────────────────┘
```

| Stage | Produces | Consumed by |
|-------|----------|-------------|
| **Git** | Commit SHA | Jenkins checks it out and passes it to `docker build` |
| **Jenkins** | Tested code, build number | Docker image tag `devops-pulse:<BUILD_NUMBER>` |
| **Docker** | Image (built inside Minikube's Docker daemon) | Kubernetes Deployment (`kubectl set image`) |
| **Kubernetes** | Running, health-checked Pods behind a Service | Prometheus discovers Pods via the Kubernetes API |
| **Prometheus** | Time-series metrics + alert rules | Grafana dashboards and the DevOps Pulse UI |
| **Grafana** | Visualisation / anomaly interpretation | People |

The dashboard closes the loop: it shows the commit, build number, image, live Pods, Prometheus targets,
firing alerts and Grafana connectivity — all from real APIs.

---

## Technology stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, Recharts, Lucide icons |
| Backend | Python 3.11, FastAPI, Uvicorn, prometheus-client, httpx |
| CI/CD | Jenkins (declarative `Jenkinsfile`, Configuration-as-Code) |
| Containers | Docker (multi-stage build) |
| Orchestration | Kubernetes on Minikube (Docker driver, Docker runtime) |
| Monitoring | Prometheus v2.55 (Kubernetes service discovery, alert rules) |
| Visualisation | Grafana 11 (provisioned datasource + dashboard) |
| Environment | Windows + WSL2 + Docker Desktop + Minikube — no cloud services |

---

## Project structure

```
Devops/
├── backend/                     FastAPI application
│   ├── app/
│   │   ├── main.py              App, middleware, /metrics, serves built frontend
│   │   ├── config.py            Environment-driven configuration
│   │   ├── metrics.py           Prometheus Counter / Gauge / Histogram / Info
│   │   ├── middleware.py        Records metrics for every request
│   │   ├── routers/
│   │   │   ├── health.py        GET /  and  GET /health
│   │   │   ├── status.py        /api/status, metrics-summary, deployment, kubernetes, events, monitoring
│   │   │   └── demo.py          /api/demo/ok|error|slow  (traffic generator)
│   │   └── services/
│   │       ├── kubernetes.py    Read-only Kubernetes API client (in-cluster ServiceAccount)
│   │       ├── monitoring.py    Prometheus (PromQL) + Grafana API checks
│   │       └── local_stats.py   Fallback stats when Prometheus isn't configured
│   ├── tests/                   pytest suite (health, API, /metrics, integrations)
│   ├── requirements.txt / requirements-dev.txt / pytest.ini
├── frontend/                    React dashboard (Vite + TS + Tailwind + Recharts)
│   └── src/  App.tsx, api.ts, useDashboard.ts, anomalies.ts, components/, test/
├── k8s/                         Application manifests
│   ├── namespace.yaml  configmap.yaml  rbac.yaml  deployment.yaml  service.yaml
├── monitoring/                  Prometheus + Grafana (kubectl apply -k monitoring/)
│   ├── kustomization.yaml
│   ├── prometheus/  prometheus.yml  alert-rules.yml  prometheus-k8s.yaml  prometheus-docker.yml
│   └── grafana/     provisioning/  dashboards/devops-pulse.json  grafana-k8s.yaml
├── jenkins/                     Local Jenkins: Dockerfile, plugins.txt, casc.yaml, setup-jenkins.ps1
├── scripts/                     deploy-minikube.ps1, port-forward.ps1
├── Dockerfile                   Multi-stage build (Node → Python)
├── Jenkinsfile                  CI/CD pipeline
├── docker-compose.yml           Optional local run without Kubernetes
└── README.md
```

### Backend API

| Method & path | Purpose |
|---------------|---------|
| `GET /` | App info (JSON) — browsers get the dashboard HTML |
| `GET /health` | Liveness/readiness probe and Docker HEALTHCHECK |
| `GET /api/status` | Overall health score + diagnostics checklist (K8s API, Pods, Service, Prometheus, Grafana) |
| `GET /api/metrics-summary` | Request rate, latency (avg/p95), error rate, totals — via PromQL, falls back to local counters |
| `GET /api/deployment` | Version, Jenkins build number, Git commit, image, replica counts |
| `GET /api/kubernetes` | Live Deployment, Pods, Service from the Kubernetes API |
| `GET /api/events` | Application events merged with Kubernetes events |
| `GET /api/monitoring` | Prometheus targets/alerts and Grafana health/datasource check |
| `GET /api/demo/ok`, `/error`, `/slow?ms=` | Safe traffic generator endpoints |
| `GET /metrics` | Prometheus scrape endpoint |
| `GET /docs` | Swagger UI |

### Prometheus metrics exposed

| Metric | Type | Meaning |
|--------|------|---------|
| `http_requests_total{method,endpoint,status_code}` | Counter | Every HTTP request |
| `http_errors_total{method,endpoint,status_code}` | Counter | 4xx/5xx responses |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `active_requests` | Gauge | Requests in flight |
| `app_uptime_seconds` | Gauge | Seconds since the process started |
| `replica_count` | Gauge | Desired replicas (from the Kubernetes API) |
| `system_health_score` | Gauge | 0–100 score from the diagnostics checklist |
| `app_info{version,environment}` | Info | Running version |
| `deployment_events_total{event_type}` | Counter | Recorded application events |

---

## Local development

Prerequisites: Python 3.11, Node.js 20.

```powershell
# Backend  (http://localhost:8000, Swagger at /docs)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Frontend (http://localhost:3000 — proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Running locally (outside Kubernetes) the dashboard honestly reports **local mode**: one instance,
metrics from the process's own counters, and Prometheus/Grafana "not configured".

---

## Docker

The [`Dockerfile`](Dockerfile) is a two-stage build:

| Instruction | Where | Why |
|-------------|-------|-----|
| `FROM node:20-alpine AS frontend-build` | stage 1 | Toolchain to build the React app |
| `WORKDIR /frontend`, `COPY package*.json`, `RUN npm ci` | stage 1 | Cached dependency layer |
| `COPY frontend/`, `RUN npm run build` | stage 1 | Produces `dist/` |
| `FROM python:3.11-slim AS runtime` | stage 2 | Small runtime image, no Node |
| `ARG BUILD_NUMBER / GIT_COMMIT …` → `ENV` | stage 2 | Jenkins metadata baked into the image |
| `COPY backend/requirements.txt`, `RUN pip install` | stage 2 | Cached dependency layer |
| `COPY backend/app`, `COPY --from=frontend-build …/dist ./static` | stage 2 | App + built UI |
| `USER appuser` | stage 2 | Non-root container |
| `EXPOSE 8000`, `HEALTHCHECK`, `CMD ["uvicorn", …]` | stage 2 | Port, health, start command |

```powershell
docker build -t devops-pulse:1.0.0 .                  # build
docker images devops-pulse                             # verify image/tag
docker run -d --name devops-pulse -p 8000:8000 devops-pulse:1.0.0
docker ps                                              # STATUS shows (healthy)
docker logs -f devops-pulse                            # request logs
curl http://localhost:8000/health
curl http://localhost:8000/metrics
docker rm -f devops-pulse
```

Optional full local stack without Kubernetes: `docker compose up -d --build`
(dashboard :8000, Prometheus :9091, Grafana :3002).

---

## Kubernetes (Minikube)

### 1. Start Minikube

```powershell
minikube start --driver=docker --container-runtime=docker --cpus=4 --memory=6144
kubectl get nodes
```

`--container-runtime=docker` matters: it lets us (and Jenkins) build images directly inside Minikube with
`minikube docker-env`, so no registry is needed and `imagePullPolicy: IfNotPresent` finds the image.

### 2. Build the image inside Minikube and deploy

```powershell
.\scripts\deploy-minikube.ps1          # does all of the following:

& minikube -p minikube docker-env --shell powershell | Invoke-Expression
docker build -t devops-pulse:1.0.0 .
kubectl apply -f k8s/namespace.yaml    # namespace first
kubectl apply -f k8s/                  # ConfigMap, RBAC, Deployment, Service
kubectl apply -k monitoring/           # Prometheus + Grafana
```

### 3. Manifests

| File | What it defines |
|------|-----------------|
| `namespace.yaml` | `devops-pulse` namespace |
| `configmap.yaml` | Environment, Prometheus/Grafana URLs → injected with `envFrom` |
| `rbac.yaml` | ServiceAccount + read-only Role so the app can show its own Pods/Events |
| `deployment.yaml` | **2 replicas**, image `devops-pulse:<tag>`, port 8000, **readiness & liveness probes** on `/health`, **requests 100m/128Mi, limits 500m/256Mi**, RollingUpdate (maxSurge 1, maxUnavailable 0), Prometheus scrape annotations, Downward-API env (`POD_NAME`, `NODE_NAME`) |
| `service.yaml` | NodePort Service: port 80 → targetPort 8000, nodePort 30080 |

### 4. Access the services

```powershell
.\scripts\port-forward.ps1
#  DevOps Pulse http://localhost:8080   Prometheus http://localhost:9090   Grafana http://localhost:3001
```

| Service | URL | Login |
|---------|-----|-------|
| DevOps Pulse | http://localhost:8080 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | anonymous viewer; admin / `devops-pulse` |
| Jenkins | http://127.0.0.1:8082 | admin / `admin` |

> `kubectl port-forward` always sends traffic to **one** Pod. To see the Service load-balance across
> replicas (the "served by" badge changing), use the NodePort tunnel instead:
> `minikube service devops-pulse-service -n devops-pulse --url`

### 5. Scaling

```powershell
kubectl get pods -n devops-pulse
kubectl scale deployment devops-pulse -n devops-pulse --replicas=3
kubectl get pods -n devops-pulse -w
```

Within ~15 s the dashboard shows **3 / 3** replicas, the Service has 3 endpoints, Prometheus shows
3 targets UP and Grafana's *Active Replicas* panel goes from 2 → 3. The app stays reachable throughout.

---

## Prometheus

- Config: [`monitoring/prometheus/prometheus.yml`](monitoring/prometheus/prometheus.yml)
- Alert rules: [`monitoring/prometheus/alert-rules.yml`](monitoring/prometheus/alert-rules.yml)

Prometheus **pulls** `GET /metrics` from each target every 15 s. Instead of hard-coding Pod IPs it uses
`kubernetes_sd_configs` (role `pod`) and keeps only Pods annotated `prometheus.io/scrape: "true"`, so new
replicas are discovered automatically. Relabelling adds `pod` and `namespace` labels.

**Demo:** open http://localhost:9090 → **Status → Targets** → job `devops-pulse` shows one row per Pod, all
**UP**. Then try these queries in **Graph**:

```promql
up{job="devops-pulse"}                                                     # 1 per healthy pod
sum(rate(http_requests_total{job="devops-pulse"}[1m]))                     # requests / second
sum by (pod) (rate(http_requests_total{job="devops-pulse"}[1m]))           # load balancing
100 * sum(rate(http_errors_total{job="devops-pulse"}[1m]))
    / sum(rate(http_requests_total{job="devops-pulse"}[1m]))               # error %
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="devops-pulse"}[1m])))  # p95
app_info                                                                    # running versions
```

Alert rules (**Alerts** tab): `DevOpsPulseTargetDown` (a Pod stops answering), `DevOpsPulseHighErrorRate`
(> 5 %), `DevOpsPulseHighLatency` (p95 > 0.5 s).

---

## Grafana

- Datasource: [`monitoring/grafana/provisioning/datasources/datasource.yml`](monitoring/grafana/provisioning/datasources/datasource.yml) → `http://prometheus:9090`
- Dashboard: [`monitoring/grafana/dashboards/devops-pulse.json`](monitoring/grafana/dashboards/devops-pulse.json)

Both are **provisioned** (loaded automatically at startup from ConfigMaps), so a fresh Grafana is ready
with no clicks. Open http://localhost:3001 (anonymous read-only; admin / `devops-pulse` to edit).

| Panel | PromQL (abridged) | How to interpret |
|-------|------------------|------------------|
| Service Health | `100 * sum(up) / count(up)` | < 100 % ⇒ a Pod is not being scraped |
| Active Replicas | `sum(up{job="devops-pulse"})` | Follows `kubectl scale` |
| Request Rate | `sum(rate(http_requests_total[1m]))` | Traffic level |
| Error Rate | errors / requests × 100 | Red above 5 % ⇒ anomaly |
| p95 Latency | `histogram_quantile(0.95, …)` | Orange/red above 0.25 / 0.5 s |
| Application Uptime | `max(app_uptime_seconds)` | Resets after a rollout |
| Request Rate by Endpoint | `sum by (endpoint) (rate(...))` | Which API is busy |
| Requests per Pod | `sum by (pod) (rate(...))` | Service load balancing across replicas |
| Target Health per Pod | `up` as a state timeline | Red bar = Pod DOWN (when / how long) |
| Responses by Status Code | `sum by (status_code) (rate(...))` | 500s appear in red |
| Running Versions | `count by (version) (app_info)` | Two versions briefly during a rolling update |

**Anomaly interpretation:** use the dashboard's *Traffic Generator* → **Error burst**. Within ~15–30 s the
Error Rate panels spike red past the dashed 5 % line, *Responses by Status Code* shows HTTP 500 bars,
Prometheus moves `DevOpsPulseHighErrorRate` to *pending → firing*, and the DevOps Pulse header turns
**Unhealthy** with an "Anomaly detected" banner. *Latency spike* does the same for the latency panels.

---

## Jenkins CI/CD

### Pipeline ([`Jenkinsfile`](Jenkinsfile))

| Stage | Commands | Output used by next stage |
|-------|----------|---------------------------|
| **Checkout** | `checkout scm`, `git rev-parse HEAD` | Commit SHA |
| **Install Dependencies** | `pip install -r requirements-dev.txt` ∥ `npm ci` | Tool environments |
| **Test** | `pytest --junitxml` (results published) ∥ `npm test` | Green tests gate the build |
| **Build Frontend** | `npm run build` (type-check + bundle) | Fails fast before Docker |
| **Build Docker Image** | `docker build --build-arg BUILD_NUMBER … -t devops-pulse:<BUILD_NUMBER>` | Image inside Minikube |
| **Deploy to Kubernetes** | `kubectl apply -f k8s/`, `kubectl set image …=devops-pulse:<BUILD_NUMBER>` | Rolling update |
| **Verify Deployment** | `kubectl rollout status`, `kubectl get pods`, in-cluster smoke test of `/health` **and** that `/api/deployment` reports this build number | Proof the new version serves traffic |
| *post failure* | `kubectl get pods`, `describe`, `get events` | Troubleshooting evidence in the build log |

**Trigger:** `pollSCM('H/2 * * * *')` — Jenkins checks the Git repository every ~2 minutes and builds when
there is a new commit. (A GitHub webhook would need Jenkins to be reachable from the internet, e.g. via a
tunnel, so polling is used for a local setup.)

### Running Jenkins locally (one-time setup)

Jenkins runs as a Docker container on Docker Desktop, attached to the `minikube` Docker network:

```powershell
# Minikube must be running first
.\jenkins\setup-jenkins.ps1 -RepoUrl https://github.com/<your-user>/<your-repo>.git -Branch main
```

The script:
1. exports a kubeconfig and Minikube's Docker TLS certificates into `jenkins/secrets/` (git-ignored);
2. builds `jenkins/Dockerfile` (Jenkins LTS + Python 3, Node 20, Docker CLI, kubectl, plugins);
3. runs Jenkins on http://localhost:8082 with `DOCKER_HOST=tcp://<minikube-ip>:2376` and `KUBECONFIG`
   pointing at Minikube — so `docker build` puts the image straight into the cluster and `kubectl` deploys it;
4. Configuration-as-Code (`jenkins/casc.yaml`) skips the setup wizard, creates user **admin**
   (password `admin` unless `-AdminPassword` is given) and a pipeline job **devops-pulse**
   ("Pipeline script from SCM" → your repo → `Jenkinsfile`).

Then open http://127.0.0.1:8082 → **devops-pulse** → **Build Now** (the first build activates SCM polling).
For a private repository add a credential (*Manage Jenkins → Credentials*) and select it in the job's SCM settings.

> **Note — declarative replicas:** the Deploy stage runs `kubectl apply -f k8s/`, so the replica count
> returns to the value in `deployment.yaml` (2) on every pipeline run. A manual `kubectl scale` is a
> temporary change; to make 3 replicas permanent, change `replicas:` in Git and push.

> **Using a different Jenkins** (e.g. one installed natively in WSL): the `Jenkinsfile` is agent-agnostic.
> The agent only needs `python3` (+venv), Node.js 20, the Docker CLI pointed at Minikube's Docker daemon
> (`minikube docker-env`) and `kubectl` with a kubeconfig for the Minikube cluster.

---

## Git workflow

> Git/GitHub is handled manually by the Git team member. The Jenkins job above expects the repository root
> to be this `Devops/` folder (Jenkinsfile at the root) and a `main` branch.

```bash
git init && git branch -M main
git add . && git commit -m "DevOps Pulse baseline"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
git checkout -b feature/version-bump      # branching
#   edit APP_VERSION in Jenkinsfile, commit, push, open PR, merge to main
git pull origin main                      # sync
git log --oneline --graph --all           # verification
git clone https://github.com/<user>/<repo>.git   # fresh copy
```

After a push to `main`, Jenkins picks up the commit within ~2 minutes and the dashboard's pipeline strip
shows the new commit SHA, build number and image tag.

---

## Testing

```powershell
cd backend;  .\.venv\Scripts\python.exe -m pytest      # 27 tests
cd frontend; npm test                                  # 7 tests (vitest + Testing Library)
cd frontend; npm run build                             # type-check + production build
```

Backend tests cover `/`, `/health`, every `/api/*` endpoint, `/metrics` content, the error counter,
label-cardinality protection, zero-initialised error series, Kubernetes Pod/Event parsing and local-mode
fallbacks. Frontend tests cover anomaly rules and rendering live data / backend-down states.

---

## Troubleshooting

| Symptom | Check | Typical cause / fix |
|---------|-------|---------------------|
| Pods `ImagePullBackOff` / `ErrImageNeverPull` | `kubectl describe pod <pod> -n devops-pulse` | Image was built in Docker Desktop instead of Minikube → run `minikube docker-env` first, or `minikube image load devops-pulse:<tag>` |
| Pods `CrashLoopBackOff` | `kubectl logs <pod> -n devops-pulse --previous` | Application error at startup |
| Pod `Running` but `0/1` ready | `kubectl describe pod …` (Readiness probe failed) | `/health` not answering on port 8000 |
| Service has no endpoints | `kubectl get endpointslices -n devops-pulse` | Selector/label mismatch or no ready Pods |
| Prometheus target DOWN | Prometheus → Status → Targets (error column) | Pod not ready, wrong port annotation |
| Dashboard says "Prometheus unreachable" | `kubectl get pods -n monitoring` | Monitoring stack not deployed: `kubectl apply -k monitoring/` |
| Grafana panels "No data" | Grafana → Connections → Data sources → Prometheus → *Test* | Prometheus down or no traffic yet (wait 1 min) |
| `port-forward`: "address already in use" | `Get-NetTCPConnection -LocalPort 9090` | Another program owns the port → `.\scripts\port-forward.ps1 -PrometheusPort 9091` (also update `PROMETHEUS_PUBLIC_URL` in `k8s/configmap.yaml` so the dashboard link matches) |
| `localhost:<port>` opens a different app than `127.0.0.1:<port>` | `wsl -- ss -ltnp` | A WSL service is listening on the same port over IPv6 → use `127.0.0.1` URLs or stop that service |
| Jenkins: `docker: Cannot connect` / `kubectl: connection refused` | `docker exec devops-pulse-jenkins kubectl get nodes` | Minikube restarted → re-run `jenkins\setup-jenkins.ps1` |
| `minikube start` fails with "certificate … not signed by CA" | — | Stale cluster from an older install → `minikube delete` then start again |

General workflow: `kubectl get` → `kubectl describe` → `kubectl logs` → `kubectl get events`.

---

## Useful commands

```powershell
# Kubernetes
kubectl get all -n devops-pulse
kubectl get pods -n devops-pulse -o wide
kubectl describe deployment devops-pulse -n devops-pulse
kubectl logs -l app=devops-pulse -n devops-pulse --tail=20
kubectl get events -n devops-pulse --sort-by=.lastTimestamp
kubectl scale deployment devops-pulse -n devops-pulse --replicas=3
kubectl rollout status deployment/devops-pulse -n devops-pulse
kubectl rollout history deployment/devops-pulse -n devops-pulse
kubectl rollout undo deployment/devops-pulse -n devops-pulse

# Docker (inside Minikube)
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
docker images devops-pulse

# Monitoring
kubectl get pods -n monitoring
curl "http://localhost:9090/api/v1/query?query=up"

# Jenkins
docker logs -f devops-pulse-jenkins
```

---

## Assessment demonstration flow

1. **Git** — show the repository, branches and commit history; make a small change (e.g. bump
   `APP_VERSION` in the `Jenkinsfile`) and `git push`.
2. **Jenkins** — within ~2 min a build starts automatically (SCM polling). Walk through the stage view:
   tests → frontend build → Docker image `devops-pulse:<N>` → deploy → verify. Show the published test results.
3. **Docker** — `docker images devops-pulse` inside Minikube shows the new tag; explain the Dockerfile
   instructions (FROM / WORKDIR / COPY / RUN / EXPOSE / CMD) and the multi-stage build.
4. **Kubernetes** — `kubectl get pods,svc -n devops-pulse`; Pods were replaced by a rolling update.
   Scale with `kubectl scale … --replicas=3` and show the app stays up.
5. **DevOps Pulse dashboard** (http://localhost:8080) — pipeline strip shows commit → build #N → image →
   3/3 pods → Prometheus targets → Grafana; diagnostics all green; Pods table lists the 3 replicas.
6. **Prometheus** (http://localhost:9090) — Status → Targets: 3 × UP; run the PromQL queries above.
7. **Grafana** (http://localhost:3001) — DevOps Pulse dashboard: Active Replicas = 3, requests per Pod,
   latency, error rate.
8. **Anomaly** — Traffic Generator → *Error burst*: Grafana error panels spike red, Prometheus alert fires,
   dashboard header turns Unhealthy. It recovers on its own after about a minute.
