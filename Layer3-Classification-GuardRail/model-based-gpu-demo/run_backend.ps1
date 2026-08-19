Write-Host "Starting Layer 3 backend..." -ForegroundColor Cyan; py -m uvicorn api:app --reload --port 8000
