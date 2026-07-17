# Clone Project 4 eval harness into vendor/ (metrics + golden/red-team datasets)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root "vendor\llm-eval-dashboard"
if (Test-Path (Join-Path $Vendor "src\metrics_basic.py")) {
    Write-Host "Harness OK: $Vendor"
    exit 0
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root "vendor") | Out-Null
if (Test-Path $Vendor) { Remove-Item $Vendor -Recurse -Force }
# Prefer local clone if present
$Local = "C:\Users\admin\Code\llm-eval-dashboard"
if (Test-Path (Join-Path $Local "src\metrics_basic.py")) {
    Write-Host "Copying local harness from $Local"
    Copy-Item -Recurse $Local $Vendor
    # Drop heavy/local-only dirs
    foreach ($d in @(".venv", "data", "reports", ".pytest_cache", "__pycache__", ".git")) {
        $p = Join-Path $Vendor $d
        if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
    }
} else {
    git clone --depth 1 https://github.com/nilima-satapathy/llm-eval-dashboard.git $Vendor
}
Write-Host "Harness ready: $Vendor"
