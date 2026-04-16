Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not available on PATH."
    }
}

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptDir "..\..")).Path
}

function Load-AsyncDsnFromEnv {
    param([string]$EnvFilePath)
    if (-not (Test-Path -LiteralPath $EnvFilePath)) {
        throw ".env file not found at '$EnvFilePath'."
    }
    $line = Get-Content -LiteralPath $EnvFilePath | Where-Object { $_ -match '^ASYNC_DATABASE_URI=' } | Select-Object -First 1
    if (-not $line) {
        throw "ASYNC_DATABASE_URI is missing in '$EnvFilePath'."
    }
    return ($line -replace '^ASYNC_DATABASE_URI=', '').Trim()
}

function Assert-LiveServer {
    param([string]$BaseUrl)
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/docs" -Method GET -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 500) {
            throw "Unexpected live-server status: $($response.StatusCode)"
        }
    }
    catch {
        throw "Live server preflight failed for '$BaseUrl'. Start uvicorn first, then rerun."
    }
}

Ensure-Command -Name "uv"

$repoRoot = Get-RepoRoot
$envFile = Join-Path $repoRoot ".env"
$asyncDsn = Load-AsyncDsnFromEnv -EnvFilePath $envFile

$env:TEST_POSTGRES_DSN = $asyncDsn
$env:RUN_LIVE_TESTS = "1"
if (-not $env:LIVE_BASE_URL) {
    $env:LIVE_BASE_URL = "http://127.0.0.1:8000"
}

Write-Step "Preflight checks"
Assert-LiveServer -BaseUrl $env:LIVE_BASE_URL
Write-Host "Using LIVE_BASE_URL=$($env:LIVE_BASE_URL)" -ForegroundColor DarkGray

Push-Location $repoRoot
try {
    Write-Step "Running points router/in-process suite"
    uv run pytest backend/app/domains/points/tests/test_point_router.py -q

    Write-Step "Running points Postgres concurrency suite (destructive schema reset)"
    uv run pytest backend/app/domains/points/tests/test_point_router_postgres.py -q

    Write-Step "Running points live-server suite"
    uv run pytest backend/tests/test_points_live_server.py -q

    Write-Step "All points suites completed successfully"
}
finally {
    Pop-Location
}
