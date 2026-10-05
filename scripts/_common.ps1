<#
  Shared helpers for the scripts in this folder (dot-source it: . "$PSScriptRoot\_common.ps1").
#>

# kubectl is often not on PATH on Windows (Docker Desktop ships one in its own bin folder).
# Returns the full path to kubectl.exe, or $null if only "minikube kubectl --" is available.
function Get-KubectlPath {
    $cmd = Get-Command kubectl -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\kubectl.exe",
        "$env:ProgramFiles\Docker\Docker\resources\bin\kubectl.exe",
        "$env:USERPROFILE\.minikube\bin\kubectl.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    return $null
}
