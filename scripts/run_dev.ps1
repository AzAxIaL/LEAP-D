# run_dev.ps1 - Development runner for LinguaSight
# Starts both backend and frontend in development mode

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [string]$BackendHost = "http://localhost:8000",
    [string]$FrontendPort = "3000"
)

$ErrorActionPreference = "Stop"

Write-Host "=== LinguaSight Development Runner ===" -ForegroundColor Cyan

# Load environment variables
if (Test-Path ".env") {
    Write-Host "Loading environment from .env..." -ForegroundColor Gray
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)\s*=\s*(.+)\s*$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Backend process
$backendJob = $null
if (-not $FrontendOnly) {
    Write-Host "Starting backend server..." -ForegroundColor Green
    
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        & uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }
    
    Write-Host "Backend starting on http://localhost:8000" -ForegroundColor Green
    Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Gray
}

# Frontend process
$frontendJob = $null
if (-not $BackendOnly) {
    Write-Host "Starting frontend dev server..." -ForegroundColor Green
    
    $frontendJob = Start-Job -ScriptBlock {
        Set-Location "$using:PWD/frontend"
        $env:VITE_API_URL = $using:BackendHost
        & npm run dev -- --port $using:FrontendPort --host
    }
    
    Write-Host "Frontend starting on http://localhost:$FrontendPort" -ForegroundColor Green
}

Write-Host ""
Write-Host "Press Ctrl+C to stop all servers" -ForegroundColor Yellow

# Wait for interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if jobs are still running
        if ($backendJob -and $backendJob.JobStateInfo.State -ne 'Running') {
            Write-Host "Backend stopped unexpectedly" -ForegroundColor Red
            break
        }
        if ($frontendJob -and $frontendJob.JobStateInfo.State -ne 'Running') {
            Write-Host "Frontend stopped unexpectedly" -ForegroundColor Red
            break
        }
    }
}
finally {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    
    if ($backendJob) {
        Stop-Job $backendJob -ErrorAction SilentlyContinue
        Remove-Job $backendJob -ErrorAction SilentlyContinue
    }
    if ($frontendJob) {
        Stop-Job $frontendJob -ErrorAction SilentlyContinue
        Remove-Job $frontendJob -ErrorAction SilentlyContinue
    }
    
    Write-Host "All servers stopped." -ForegroundColor Gray
}
