<#
.SYNOPSIS
  Manual (non-Jenkins) deployment: build the image inside Minikube and apply all manifests.
.EXAMPLE
  .\scripts\deploy-minikube.ps1              # image devops-pulse:1.0.0
  .\scripts\deploy-minikube.ps1 -Tag 1.0.1   # build a new tag and roll it out
#>
param([string]$Tag = "1.0.0")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "==> Pointing docker CLI at Minikube's Docker daemon" -ForegroundColor Cyan
& minikube -p minikube docker-env --shell powershell | Invoke-Expression

try {
    Write-Host "==> docker build -t devops-pulse:$Tag ." -ForegroundColor Cyan
    docker build -t "devops-pulse:$Tag" --build-arg "IMAGE_NAME=devops-pulse:$Tag" .
    if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
} finally {
    Remove-Item Env:DOCKER_HOST, Env:DOCKER_TLS_VERIFY, Env:DOCKER_CERT_PATH, Env:MINIKUBE_ACTIVE_DOCKERD -ErrorAction SilentlyContinue
}

Write-Host "==> Applying Kubernetes manifests" -ForegroundColor Cyan
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
kubectl apply -k monitoring/
kubectl -n devops-pulse set image deployment/devops-pulse "devops-pulse=devops-pulse:$Tag"
kubectl -n devops-pulse annotate deployment/devops-pulse --overwrite "kubernetes.io/change-cause=Manual deploy devops-pulse:$Tag"
kubectl -n devops-pulse annotate deployment/devops-pulse --overwrite "kubernetes.io/change-cause=Manual deploy devops-pulse:$Tag"

Write-Host "==> Waiting for rollouts" -ForegroundColor Cyan
kubectl -n devops-pulse rollout status deployment/devops-pulse --timeout=180s
kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s
kubectl get pods -n devops-pulse
kubectl get pods -n monitoring
Write-Host "Done. Run .\scripts\port-forward.ps1 to open the dashboard, Prometheus and Grafana." -ForegroundColor Green
