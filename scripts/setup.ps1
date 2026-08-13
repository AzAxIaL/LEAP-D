# EFL Speaking Analysis Platform - Setup Script for Windows

Write-Host "=== EFL Speaking Analysis Platform Setup ===" -ForegroundColor Cyan

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

if (!(Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Running database migrations..." -ForegroundColor Yellow
alembic upgrade head

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
Write-Host "  Backend:  cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  Frontend: cd frontend; npm run dev" -ForegroundColor White
