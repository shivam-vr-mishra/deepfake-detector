# =============================================================
# DeepFake Detector - one-command bootstrap (Windows PowerShell)
#
# Reads DB_TARGET from .env to decide which database to use:
#   DB_TARGET=neon  (default) -> skip local postgres, connect to Neon
#   DB_TARGET=local           -> launch the postgres container locally
#
# The Grafana + Loki + Promtail observability stack is started by default
# (Grafana on http://localhost:3001). Pass -NoObservability to skip it.
#
# Override at runtime:
#   .\start.ps1                       # uses .env DB_TARGET, observability ON
#   .\start.ps1 local                 # force local Postgres
#   .\start.ps1 neon                  # force Neon
#   .\start.ps1 prod                  # production override (docker-compose.prod.yml)
#   .\start.ps1 -NoObservability      # skip Grafana / Loki / Promtail
# =============================================================
param(
    [ValidateSet("neon", "local", "prod", "")]
    [string]$Target = "",

    # The observability stack (Loki + Promtail + Grafana) is on by default.
    # Use -NoObservability to skip it (e.g. on a low-RAM machine).
    [switch]$NoObservability
)

$WithObservability = -not $NoObservability

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Green  ($m) { Write-Host $m -ForegroundColor Green }
function Write-Yellow ($m) { Write-Host $m -ForegroundColor Yellow }
function Write-Red    ($m) { Write-Host $m -ForegroundColor Red }
function Write-Bold   ($m) { Write-Host $m -ForegroundColor Cyan }

# ---------- 1. .env ----------
Write-Host "[1/5] Checking environment file..."
if (-Not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Yellow "    .env created from .env.example - open it and fill in real secrets."
    Write-Yellow "    At minimum set DATABASE_URL_NEON, SMTP_USER, SMTP_PASSWORD, RAZORPAY_*."
    exit 1
}

# Read DB_TARGET from .env (and command-line override wins)
$envText = Get-Content .env -Raw
$dbTargetFromEnv = "neon"
$match = [regex]::Match($envText, '(?m)^DB_TARGET=(.*)$')
if ($match.Success) {
    $dbTargetFromEnv = $match.Groups[1].Value.Trim().Trim('"').Trim("'")
}
if (-not $Target) { $Target = $dbTargetFromEnv }
if (-not $Target) { $Target = "neon" }

if ($Target -notin @("neon", "local", "prod")) {
    Write-Red "Unknown DB target: $Target"
    Write-Host "Use one of: neon | local | prod"
    exit 2
}

# ---------- 2. Pick compose files ----------
$composeArgs = @("-f", "infra/docker-compose.yml")
switch ($Target) {
    "neon"  { $composeArgs += @("-f", "infra/docker-compose.neon.yml") }
    "local" { }   # base compose includes postgres container
    "prod"  { $composeArgs += @("-f", "infra/docker-compose.prod.yml") }
}
if ($WithObservability) {
    $composeArgs += @("-f", "infra/docker-compose.observability.yml")
}

Write-Host ""
Write-Bold "================================================================"
Write-Bold "  DeepFake Detector - booting with DB_TARGET=$Target"
Write-Bold "================================================================"
switch ($Target) {
    "neon"  { Write-Green  "  Database: Neon (managed Postgres) - local postgres container disabled" }
    "local" { Write-Green  "  Database: local Docker Postgres" }
    "prod"  { Write-Yellow "  Database: external (Neon/RDS) - production hardening enabled" }
}
Write-Bold "================================================================"

# Sanity check that the right URL is set
if ($Target -eq "neon") {
    if ($envText -notmatch '(?m)^DATABASE_URL_NEON=postgres') {
        Write-Red "ERROR: DB_TARGET=neon but DATABASE_URL_NEON is not set in .env."
        Write-Host "Open .env and paste your Neon connection string from the Neon dashboard."
        exit 3
    }
}

# ---------- 3. Build ----------
Write-Host ""
Write-Host "[2/5] Building images..."
& docker compose @composeArgs --env-file .env build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ---------- 4. Up ----------
Write-Host ""
Write-Host "[3/5] Starting services..."
& docker compose @composeArgs --env-file .env up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ---------- 5. Wait for backend, then bootstrap schema ----------
Write-Host ""
Write-Host "[4/5] Waiting for backend to become healthy at http://localhost:8000/health ..."

$prevErrorPref = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"

$attempts = 0
$maxAttempts = 60   # 60 * 5s = 5 min
$healthy = $false
while (-not $healthy -and $attempts -lt $maxAttempts) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" `
                                  -UseBasicParsing -TimeoutSec 3 2>$null
        if ($resp -and $resp.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        # Backend not listening yet — retry.
    }
    Start-Sleep -Seconds 5
    $attempts++
    Write-Host "." -NoNewline
}
Write-Host ""

$ErrorActionPreference = $prevErrorPref

if (-not $healthy) {
    Write-Red "Backend did not become healthy in 5 minutes."
    Write-Yellow ("Inspect logs: docker compose " + ($composeArgs -join ' ') + " logs -f backend")
    exit 4
}
Write-Green "    Backend is up."

# Show the DB profile the backend resolved to.
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host ("    DB profile: {0}, host: {1}, ok: {2}" -f `
                $health.db.profile, $health.db.host, $health.db.ok)
} catch { }

Write-Host ""
Write-Host "[5/5] Ensuring database schema exists..."
$prevErrorPref = $ErrorActionPreference
$ErrorActionPreference = "Continue"

# Bootstrap is idempotent (CREATE TABLE IF NOT EXISTS under the hood).
$bootstrapPy = "from app.db import bootstrap_schema; bootstrap_schema(); print('schema-ok')"
$bootstrapOut = & docker compose @composeArgs --env-file .env exec -T backend `
                  python -c $bootstrapPy 2>&1 | Out-String
$ErrorActionPreference = $prevErrorPref

if ($LASTEXITCODE -eq 0 -and $bootstrapOut -match "schema-ok") {
    Write-Green "    Schema is up to date."
} else {
    Write-Yellow "    Schema bootstrap returned a non-zero exit code; details below:"
    Write-Host $bootstrapOut
}

# ---------- Summary ----------
$composeStr = $composeArgs -join ' '
Write-Host ""
Write-Green "DeepFake Detector is up."
Write-Host @"

  DB target:       $Target
  Frontend:        http://localhost:3000
  Backend (API):   http://localhost:8000/docs
  Health check:    http://localhost:8000/health
  MinIO console:   http://localhost:9001
  Flower:          http://localhost:5555$(if ($WithObservability) {"
  Grafana logs:    http://localhost:3001  (admin / `$GRAFANA_PASSWORD)"})

Useful commands:
  Logs:            docker compose $composeStr logs -f
  Stop:            docker compose $composeStr down
  Switch to local: .\start.ps1 local
  Switch to Neon:  .\start.ps1 neon
  Production:      .\start.ps1 prod
  Skip Grafana:    .\start.ps1 -NoObservability

"@
