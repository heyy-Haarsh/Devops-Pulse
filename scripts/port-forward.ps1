<#
.SYNOPSIS
  Opens local ports to the services running in Minikube (Ctrl+C stops all of them).
    App        http://localhost:8080
    Prometheus http://localhost:9090
    Grafana    http://localhost:3001
  Forwards bind to 127.0.0.1 explicitly so a port already used by another program
  fails loudly instead of silently falling back to IPv6.
#>
param(
    [int]$AppPort = 8080,
    [int]$PrometheusPort = 9090,
    [int]$GrafanaPort = 3001
)

$forwards = @(
    @{ ns = "devops-pulse"; svc = "svc/devops-pulse-service"; map = "${AppPort}:80" },
    @{ ns = "monitoring";   svc = "svc/prometheus";           map = "${PrometheusPort}:9090" },
    @{ ns = "monitoring";   svc = "svc/grafana";              map = "${GrafanaPort}:3000" }
)

$jobs = foreach ($f in $forwards) {
    Start-Job -ScriptBlock {
        param($ns, $svc, $map)
        # Restart the forward if the target Pod is replaced (e.g. after a rollout)
        while ($true) {
            kubectl -n $ns port-forward --address 127.0.0.1 $svc $map 2>&1
            Start-Sleep 2
        }
    } -ArgumentList $f.ns, $f.svc, $f.map
}

Write-Host "DevOps Pulse  -> http://localhost:$AppPort" -ForegroundColor Green
Write-Host "Prometheus    -> http://localhost:$PrometheusPort" -ForegroundColor Green
Write-Host "Grafana       -> http://localhost:$GrafanaPort  (admin / devops-pulse)" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop."
try {
    while ($true) { $jobs | Receive-Job; Start-Sleep 2 }
} finally {
    $jobs | Stop-Job -PassThru | Remove-Job
}
