<#
.SYNOPSIS
  Manual (non-Jenkins) deployment: build the image inside Minikube and apply all manifests.
  Starts Minikube first if it is not running (Docker Desktop must be running).
.EXAMPLE
  .\scripts\deploy-minikube.ps1              # image devops-pulse:1.0.0
  .\scripts\deploy-minikube.ps1 -Tag 1.0.1   # build a new tag and roll it out
#>
param([string]$Tag = "1.0.0")

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
. "$PSScriptRoot\_common.ps1"

$kubectlPath = Get-KubectlPath
if ($kubectlPath) {
    function kubectl { & $kubectlPath @args }
} else {
    Write-Host "kubectl not found - using 'minikube kubectl --'" -ForegroundColor Yellow
    function kubectl { & minikube kubectl -- @args }
}

Remove-Item Env:DOCKER_HOST, Env:DOCKER_TLS_VERIFY, Env:DOCKER_CERT_PATH, Env:MINIKUBE_ACTIVE_DOCKERD -ErrorAction SilentlyContinue
$apiServer = & minikube -p minikube status --format "{{.APIServer}}"
if ($apiServer -ne "Running") {
    Write-Host "==> Minikube is not running - starting it" -ForegroundColor Cyan
    & minikube start -p minikube --driver=docker --container-runtime=docker
    if ($LASTEXITCODE -ne 0) { throw "minikube start failed - is Docker Desktop running ('docker version' should show a Server section)?" }
}

Write-Host "==> Pointing docker CLI at Minikube's Docker daemon" -ForegroundColor Cyan
$dockerEnv = & minikube -p minikube docker-env --shell powershell
if ($LASTEXITCODE -ne 0) { throw "minikube docker-env failed: $dockerEnv" }
$dockerEnv | Invoke-Expression

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
$currentImage = kubectl -n devops-pulse get deployment/devops-pulse -o "jsonpath={.spec.template.spec.containers[0].image}"
kubectl -n devops-pulse set image deployment/devops-pulse "devops-pulse=devops-pulse:$Tag"
if ($currentImage -eq "devops-pulse:$Tag") {
    # Same tag was rebuilt: the Pod template did not change, so force new Pods to pick up the new image
    kubectl -n devops-pulse rollout restart deployment/devops-pulse
}
kubectl -n devops-pulse annotate deployment/devops-pulse --overwrite "kubernetes.io/change-cause=Manual deploy devops-pulse:$Tag"

Write-Host "==> Waiting for rollouts" -ForegroundColor Cyan
kubectl -n devops-pulse rollout status deployment/devops-pulse --timeout=180s
kubectl -n monitoring rollout status deployment/prometheus --timeout=180s
kubectl -n monitoring rollout status deployment/grafana --timeout=180s
kubectl get pods -n devops-pulse
kubectl get pods -n monitoring
Write-Host "Done. Run .\scripts\port-forward.ps1 to open the dashboard, Prometheus and Grafana." -ForegroundColor Green
