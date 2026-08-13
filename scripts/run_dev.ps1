# run_dev.ps1 - Run LEAP-D in development mode (PowerShell)

Write-Host "=== LEAP-D Development Mode ===" -ForegroundColor Cyan

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "Error: Virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Start backend in background
Write-Host "Starting backend server..." -ForegroundColor Yellow
Start-Process -FilePath "uvicorn" -ArgumentList "backend.app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -NoNewWindow
Write-Host "Backend running on http://localhost:8000" -ForegroundColor Green

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend dev server..." -ForegroundColor Yellow
Set-Location frontend
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -NoNewWindow
Set-Location ..

Write-Host "`n=== LEAP-D is running ===" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop all servers" -ForegroundColor Yellow
