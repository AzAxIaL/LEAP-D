# run_prod.ps1 - Production runner for LinguaSight
# Starts backend with gunicorn and serves pre-built frontend

param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [int]$Workers = 2
)

$ErrorActionPreference = "Stop"

Write-Host "=== LinguaSight Production Server ===" -ForegroundColor Cyan

# Validate environment
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found. Using default configuration." -ForegroundColor Yellow
}

# Check if frontend is built
if (-not (Test-Path "frontend/dist")) {
    Write-Host "Frontend not built. Building now..." -ForegroundColor Yellow
    Set-Location "frontend"
    & npm run build
    Set-Location ..
}

Write-Host "Starting production server..." -ForegroundColor Green
Write-Host "Server: http://localhost:$Port" -ForegroundColor Green

# Start with gunicorn for production
& gunicorn app.main:app `
    --workers $Workers `
    --worker-class uvicorn.workers.UvicornWorker `
    --bind "$Host`:$Port" `
    --timeout 120 `
    --keep-alive 5 `
    --access-logfile logs/access.log `
    --error-logfile logs/error.log
