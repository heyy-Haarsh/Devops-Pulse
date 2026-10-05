<#
.SYNOPSIS
  Starts a local Jenkins (in Docker Desktop) that can build into and deploy to Minikube.

.DESCRIPTION
  1. Reads Minikube's IP and exports credentials Jenkins needs into jenkins/secrets/ (git-ignored):
       - kubeconfig       -> kubectl talks to https://<minikube-ip>:8443
       - docker/*.pem     -> docker CLI talks to Minikube's Docker daemon (tcp://<minikube-ip>:2376)
  2. Builds the Jenkins image (jenkins/Dockerfile).
  3. Runs Jenkins on the "minikube" Docker network so it can reach the cluster directly.

  Images built by the pipeline therefore land directly inside Minikube — exactly what
  `minikube docker-env` does for a developer — so no image registry is needed.

.EXAMPLE
  .\jenkins\setup-jenkins.ps1 -RepoUrl https://github.com/<you>/devops-pulse.git
#>
param(
    [string]$RepoUrl = "https://github.com/CHANGE-ME/devops-pulse.git",
    [string]$Branch = "main",
    [string]$AdminPassword = "admin",
    [int]$Port = 8082
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$secrets = Join-Path $PSScriptRoot "secrets"
$container = "devops-pulse-jenkins"
. (Join-Path $root "scripts\_common.ps1")
$kubectlPath = Get-KubectlPath
if ($kubectlPath) {
    function kubectl { & $kubectlPath @args }
} else {
    function kubectl { & minikube kubectl -- @args }
}

# Make sure the docker CLI talks to Docker Desktop, not to Minikube's daemon
Remove-Item Env:DOCKER_HOST, Env:DOCKER_TLS_VERIFY, Env:DOCKER_CERT_PATH, Env:MINIKUBE_ACTIVE_DOCKERD -ErrorAction SilentlyContinue

Write-Host "==> Checking Minikube" -ForegroundColor Cyan
$ip = (minikube ip).Trim()
if (-not $ip) { throw "Minikube is not running. Start it with: minikube start --driver=docker --container-runtime=docker" }
Write-Host "    Minikube IP: $ip"

Write-Host "==> Exporting kubeconfig and Docker TLS certs to jenkins/secrets" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path (Join-Path $secrets "docker") | Out-Null
$kubeconfig = kubectl config view --minify --flatten --context=minikube -o yaml | Out-String
$kubeconfig = $kubeconfig -replace "server: https://[^\s]+", "server: https://${ip}:8443"
[IO.File]::WriteAllText((Join-Path $secrets "kubeconfig"), $kubeconfig)
$certs = Join-Path $env:USERPROFILE ".minikube\certs"
foreach ($f in "ca.pem", "cert.pem", "key.pem") {
    Copy-Item (Join-Path $certs $f) (Join-Path $secrets "docker\$f") -Force
}

Write-Host "==> Building Jenkins image" -ForegroundColor Cyan
docker build -t devops-pulse-jenkins:latest $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Jenkins image build failed" }

Write-Host "==> (Re)starting Jenkins container" -ForegroundColor Cyan
docker rm -f $container 2>$null | Out-Null
# Fixed IP: otherwise, after a Docker Desktop restart, Jenkins can come up first and take
# Minikube's address (.2), and "minikube start" then fails with "Address already in use".
$jenkinsIp = $ip -replace '\.\d+$', '.10'
docker run -d --name $container --restart unless-stopped `
    --network minikube --ip $jenkinsIp `
    -p "${Port}:8080" `
    -v devops-pulse-jenkins-home:/var/jenkins_home `
    --mount "type=bind,source=$secrets,target=/var/jenkins_secrets,readonly" `
    -e "DOCKER_HOST=tcp://${ip}:2376" `
    -e "DOCKER_TLS_VERIFY=1" `
    -e "DOCKER_CERT_PATH=/var/jenkins_secrets/docker" `
    -e "KUBECONFIG=/var/jenkins_secrets/kubeconfig" `
    -e "REPO_URL=$RepoUrl" `
    -e "REPO_BRANCH=$Branch" `
    -e "JENKINS_ADMIN_PASSWORD=$AdminPassword" `
    -e "JENKINS_URL=http://localhost:$Port/" `
    devops-pulse-jenkins:latest | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to start Jenkins" }

Write-Host "==> Waiting for Jenkins to come up" -ForegroundColor Cyan
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 3
    try {
        $code = (Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/login" -TimeoutSec 3).StatusCode
        if ($code -eq 200) { break }
    } catch { }
}

Write-Host "==> Verifying tools inside Jenkins" -ForegroundColor Cyan
docker exec $container sh -c "docker version --format 'docker server (minikube): {{.Server.Version}}' && kubectl get nodes && python3 --version && node --version"

Write-Host ""
Write-Host "Jenkins is ready: http://localhost:$Port  (user: admin / password: $AdminPassword)" -ForegroundColor Green
Write-Host "Pipeline job 'devops-pulse' builds $RepoUrl ($Branch). Click 'Build Now' once to activate SCM polling."
