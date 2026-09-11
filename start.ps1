# Start BE_BOM Backend
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Starting BE_BOM (Python FastAPI)" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

$venvPath = "venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
    Write-Host "Virtual environment activated!`n" -ForegroundColor Green
} else {
    Write-Host "Warning: Virtual environment not found" -ForegroundColor Yellow
    Write-Host "Running with system Python...`n" -ForegroundColor Yellow
}

Write-Host "Starting uvicorn server on port 8000..." -ForegroundColor Yellow
Write-Host "API Docs will be available at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Admin Panel: http://localhost:8000/admin`n" -ForegroundColor Cyan

python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0 --proxy-headers --forwarded-allow-ips="*"
