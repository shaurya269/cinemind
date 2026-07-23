<#
.SYNOPSIS
    One-shot setup + launch for CineMind on a fresh Windows machine.

.DESCRIPTION
    Run this from the cinemind_phase1/ folder after cloning the repo.
    It will, in order:
      1. Check/install prerequisites (Python, Node.js, Docker Desktop via winget)
      2. Create a Python venv and install requirements.txt
      3. Download the MovieLens 100K dataset if missing
      4. Prompt for API keys and write .env if missing (never overwrites an existing one)
      5. Run the ML pipeline (scripts 01-04) only if artifacts are missing
      6. Start Docker Desktop and bring up the backend stack (API + Qdrant + Postgres + Redis + Neo4j)
      7. npm install + npm run dev for the React frontend
      8. Open the app in your browser

    Safe to re-run: every step is skipped if its output already exists.

.NOTES
    Windows/PowerShell only. Run from an elevated (Administrator) prompt if
    Docker Desktop needs to be installed via winget.
#>

[CmdletBinding()]
param(
    [switch]$SkipPipeline,   # skip the ML training pipeline even if artifacts are missing
    [switch]$SkipDocker,     # skip Docker/backend entirely (frontend-only, degraded mode)
    [switch]$NoBrowser       # don't auto-open the browser at the end
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Write-Step($msg) {
    Write-Host ""
    Write-Host ">> $msg" -ForegroundColor Cyan
}
function Write-Ok($msg) {
    Write-Host "   OK: $msg" -ForegroundColor Green
}
function Write-Warn($msg) {
    Write-Host "   WARN: $msg" -ForegroundColor Yellow
}
function Write-Fail($msg) {
    Write-Host "   FAIL: $msg" -ForegroundColor Red
}

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

# --- Python ---
if (-not (Test-Command "python")) {
    Write-Fail "Python not found."
    if (Test-Command "winget") {
        Write-Host "   Installing Python 3.11 via winget..."
        winget install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements
        Write-Warn "Python was just installed. Close this window and re-run the script in a NEW terminal so PATH updates take effect."
        exit 1
    } else {
        Write-Fail "winget not available either. Install Python 3.10+ manually from https://python.org/downloads and re-run."
        exit 1
    }
} else {
    Write-Ok "Python found: $(python --version)"
}

# --- Node.js ---
if (-not (Test-Command "node")) {
    Write-Fail "Node.js not found."
    if (Test-Command "winget") {
        Write-Host "   Installing Node.js LTS via winget..."
        winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
        Write-Warn "Node.js was just installed. Close this window and re-run the script in a NEW terminal so PATH updates take effect."
        exit 1
    } else {
        Write-Fail "winget not available either. Install Node.js 18+ manually from https://nodejs.org and re-run."
        exit 1
    }
} else {
    Write-Ok "Node.js found: $(node --version)"
}

# --- Docker Desktop ---
$dockerAvailable = -not $SkipDocker
if (-not $SkipDocker) {
    if (-not (Test-Command "docker")) {
        Write-Fail "Docker not found."
        if (Test-Command "winget") {
            Write-Host "   Installing Docker Desktop via winget (this can take a few minutes)..."
            winget install --id Docker.DockerDesktop -e --source winget --accept-package-agreements --accept-source-agreements
            Write-Warn "Docker Desktop was just installed."
            Write-Warn "You must now: (1) launch Docker Desktop manually, (2) accept its license terms,"
            Write-Warn "(3) possibly reboot if prompted, then re-run this script."
            exit 1
        } else {
            Write-Fail "winget not available. Install Docker Desktop manually from https://www.docker.com/products/docker-desktop and re-run."
            Write-Warn "Continuing WITHOUT Docker -- backend will run in degraded mode (no cache/graph/persistent feedback)."
            $dockerAvailable = $false
        }
    } else {
        Write-Ok "Docker found: $(docker --version)"
    }
}

# ---------------------------------------------------------------------------
# 2. Python virtual environment + dependencies
# ---------------------------------------------------------------------------
Write-Step "Setting up Python virtual environment"

if (-not (Test-Path "$root\.venv")) {
    python -m venv "$root\.venv"
    Write-Ok "Created .venv"
} else {
    Write-Ok ".venv already exists"
}

$venvPython = "$root\.venv\Scripts\python.exe"
$venvPip = "$root\.venv\Scripts\pip.exe"

Write-Step "Installing Python dependencies (this can take a few minutes on first run)"
& $venvPip install --upgrade pip --quiet
& $venvPip install -r "$root\requirements.txt"
Write-Ok "Python dependencies installed"

# ---------------------------------------------------------------------------
# 3. Dataset
# ---------------------------------------------------------------------------
Write-Step "Checking MovieLens 100K dataset"

$dataDir = "$root\data\ml-100k"
if (-not (Test-Path "$dataDir\u.data")) {
    Write-Host "   Dataset not found. Downloading ml-100k.zip..."
    New-Item -ItemType Directory -Force -Path "$root\data" | Out-Null
    $zipPath = "$root\data\ml-100k.zip"
    Invoke-WebRequest -Uri "https://files.grouplens.org/datasets/movielens/ml-100k.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath "$root\data" -Force
    Remove-Item $zipPath
    Write-Ok "Dataset downloaded to $dataDir"
} else {
    Write-Ok "Dataset already present at $dataDir"
}

# ---------------------------------------------------------------------------
# 4. .env / API keys
# ---------------------------------------------------------------------------
Write-Step "Checking .env configuration"

$envPath = "$root\.env"
if (-not (Test-Path $envPath)) {
    Write-Host "   No .env found. Let's set up API keys (press Enter to skip any optional one)."
    Write-Host "   At least one LLM key (Anthropic or Groq) is required for chat/explanations/onboarding to work."
    Write-Host ""

    $anthropicKey = Read-Host "   ANTHROPIC_API_KEY (optional, paid, press Enter to skip)"
    $groqKey = ""
    if ([string]::IsNullOrWhiteSpace($anthropicKey)) {
        $groqKey = Read-Host "   GROQ_API_KEY (free tier, get one at console.groq.com -- recommended if skipping Anthropic)"
    }
    $omdbKey = Read-Host "   OMDB_API_KEY (optional, posters/plot/cast, free at omdbapi.com, press Enter to skip)"
    $langfusePublic = Read-Host "   LANGFUSE_PUBLIC_KEY (optional, LLM tracing, press Enter to skip)"
    $langfuseSecret = ""
    if (-not [string]::IsNullOrWhiteSpace($langfusePublic)) {
        $langfuseSecret = Read-Host "   LANGFUSE_SECRET_KEY"
    }

    $envLines = @(
        "ANTHROPIC_API_KEY=$anthropicKey",
        "GROQ_API_KEY=$groqKey",
        "OMDB_API_KEY=$omdbKey",
        "LANGFUSE_PUBLIC_KEY=$langfusePublic",
        "LANGFUSE_SECRET_KEY=$langfuseSecret",
        "LANGFUSE_HOST=https://cloud.langfuse.com"
    )
    Set-Content -Path $envPath -Value $envLines -Encoding utf8
    Write-Ok "Wrote .env"

    if ([string]::IsNullOrWhiteSpace($anthropicKey) -and [string]::IsNullOrWhiteSpace($groqKey)) {
        Write-Warn "No LLM key provided -- chat/explanations/onboarding will fall back to retrieval-only mode."
    }
} else {
    Write-Ok ".env already exists -- leaving it untouched"
}

# ---------------------------------------------------------------------------
# 5. ML pipeline (only if artifacts missing)
# ---------------------------------------------------------------------------
if (-not $SkipPipeline) {
    Write-Step "Checking trained model artifacts"

    $artifactsDir = "$root\artifacts"
    New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null

    $pipelineSteps = @(
        @{ Script = "src\01_data_exploration.py"; Check = "data\train_positives.csv" },
        @{ Script = "src\02_rbm_baseline.py";      Check = $null },
        @{ Script = "src\03_content_embeddings.py"; Check = "artifacts\content_vecs.npy" },
        @{ Script = "src\04_two_tower.py";          Check = "artifacts\two_tower.pt" },
        @{ Script = "src\06_evaluation.py";         Check = "artifacts\results.csv" }
    )

    foreach ($step in $pipelineSteps) {
        $checkPath = if ($step.Check) { "$root\$($step.Check)" } else { $null }
        if ($checkPath -and (Test-Path $checkPath)) {
            Write-Ok "$($step.Script) already run (found $($step.Check))"
        } else {
            Write-Host "   Running $($step.Script) ..."
            & $venvPython "$root\$($step.Script)"
            if ($LASTEXITCODE -ne 0) {
                Write-Fail "$($step.Script) failed. Fix the error above and re-run this script."
                exit 1
            }
            Write-Ok "$($step.Script) complete"
        }
    }

    # OMDb enrichment: optional, needs OMDB_API_KEY, resumable
    if (-not (Test-Path "$root\artifacts\movie_meta.csv")) {
        $envContent = Get-Content $envPath -Raw
        if ($envContent -match "OMDB_API_KEY=\S") {
            Write-Host "   Running src\07_omdb_enrichment.py (poster/plot/cast) ..."
            & $venvPython "$root\src\07_omdb_enrichment.py"
            Write-Ok "OMDb enrichment complete"
        } else {
            Write-Warn "No OMDB_API_KEY set -- skipping poster/plot/cast enrichment. Recommendations will still work, without posters."
        }
    } else {
        Write-Ok "OMDb enrichment already run (found artifacts\movie_meta.csv)"
    }
} else {
    Write-Warn "Skipping ML pipeline (-SkipPipeline passed)"
}

# ---------------------------------------------------------------------------
# 6. Backend (Docker stack)
# ---------------------------------------------------------------------------
if ($dockerAvailable) {
    Write-Step "Starting backend Docker stack"

    # Make sure the Docker engine is actually running, not just installed
    $dockerUp = $false
    try {
        docker info *> $null
        $dockerUp = $true
    } catch {
        $dockerUp = $false
    }

    if (-not $dockerUp) {
        Write-Host "   Docker Desktop engine not running -- attempting to start it..."
        $dockerDesktopExe = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerDesktopExe) {
            Start-Process $dockerDesktopExe
            Write-Host "   Waiting for Docker engine to become ready (up to 90s)..."
            $waited = 0
            while ($waited -lt 90) {
                Start-Sleep -Seconds 3
                $waited += 3
                try {
                    docker info *> $null
                    $dockerUp = $true
                    break
                } catch { }
            }
        }
    }

    if ($dockerUp) {
        Write-Ok "Docker engine is running"
        docker compose --env-file "$root\.env" -f "$root\backend\docker-compose.yml" up -d --build
        Write-Ok "Backend containers started"

        Write-Host "   Waiting for API health check..."
        $healthy = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 2
            try {
                $resp = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3
                if ($resp.status -eq "ok") { $healthy = $true; break }
            } catch { }
        }
        if ($healthy) {
            Write-Ok "Backend healthy at http://localhost:8000"
        } else {
            Write-Warn "Backend did not report healthy within 60s -- check 'docker compose -f backend/docker-compose.yml logs api'"
        }

        # Load Neo4j graph once (idempotent, safe to call every run)
        Write-Host "   Loading graph data into Neo4j (idempotent, safe to repeat)..."
        & $venvPython "$root\src\08_neo4j_graph.py" 2>&1 | Out-Null
        Write-Ok "Graph data loaded"
    } else {
        Write-Fail "Docker engine did not become ready. Start Docker Desktop manually and re-run this script."
        Write-Warn "Continuing to launch the frontend anyway -- API calls will fail until the backend is up."
    }
} else {
    Write-Warn "Skipping Docker backend (degraded mode: no cache/graph/persistent feedback, numpy/SQLite fallback only)"
    Write-Host "   To still get recommendations without Docker, run manually: .venv\Scripts\python -m uvicorn backend.main:app --port 8000"
}

# ---------------------------------------------------------------------------
# 7. Frontend
# ---------------------------------------------------------------------------
Write-Step "Setting up React frontend"

Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) {
    npm install
    Write-Ok "npm dependencies installed"
} else {
    Write-Ok "node_modules already present"
}

Write-Step "Starting the frontend dev server (new window)"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; node node_modules/vite/bin/vite.js"

Start-Sleep -Seconds 4
Set-Location $root

# ---------------------------------------------------------------------------
# 8. Open browser
# ---------------------------------------------------------------------------
Write-Step "Done"
Write-Ok "Frontend: http://localhost:5173"
if ($dockerAvailable) { Write-Ok "Backend:  http://localhost:8000/health" }

if (-not $NoBrowser) {
    Start-Process "http://localhost:5173"
}

Write-Host ""
Write-Host "The frontend dev server is running in its own window -- close that window (or Ctrl+C in it) to stop it." -ForegroundColor DarkGray
if ($dockerAvailable) {
    Write-Host "To stop the backend later: docker compose -f backend\docker-compose.yml down" -ForegroundColor DarkGray
}
