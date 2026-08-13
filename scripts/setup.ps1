# LEAP-D: Longitudinal ESL Assessment of Proficiency and Disfluency - Setup Script for Windows

Write-Host "=== LEAP-D Setup ===" -ForegroundColor Cyan

# Check uv
Write-Host "`nChecking uv..." -ForegroundColor Yellow
$uvVersion = uv --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "uv not found. Please install uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $uvVersion" -ForegroundColor Green

# Check Python
Write-Host "`nChecking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Check Node.js
Write-Host "`nChecking Node.js..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $nodeVersion" -ForegroundColor Green

# Check FFmpeg
Write-Host "`nChecking FFmpeg..." -ForegroundColor Yellow
$ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0) {
    Write-Host "FFmpeg not found. Install with: choco install ffmpeg" -ForegroundColor Yellow
} else {
    Write-Host "Found: $ffmpegVersion" -ForegroundColor Green
}

# Setup Backend
Write-Host "`n=== Setting up Backend ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot\..\backend

if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment with uv..." -ForegroundColor Yellow
    uv venv
}

Write-Host "Installing Python dependencies with uv..." -ForegroundColor Yellow
uv pip install -r requirements.txt

Write-Host "Running database migrations..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1; alembic upgrade head; deactivate

# Setup Frontend
Write-Host "`n=== Setting up Frontend ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot\..\frontend

if (!(Test-Path "node_modules")) {
    Write-Host "Installing Node dependencies..." -ForegroundColor Yellow
    npm install
}

# Create .env if not exists
if (!(Test-Path "$PSScriptRoot\..\backend\.env")) {
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item "$PSScriptRoot\..\.env.example" "$PSScriptRoot\..\backend\.env"
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host "`nTo start the application:" -ForegroundColor Cyan
Write-Host "  Backend:  cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  Frontend: cd frontend; npm run dev" -ForegroundColor White
