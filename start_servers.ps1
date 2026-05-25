# Start servers
$ErrorActionPreference = "SilentlyContinue"

# Kill any existing processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# Set working directory
$workDir = "F:\opencode\001\stock_platform"

# Start backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; Write-Host 'Starting backend...'; python -m uvicorn api.main:app --reload --port 8000" -WindowStyle Normal

Start-Sleep -Seconds 3

# Start frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$workDir'; Write-Host 'Starting frontend...'; python -m streamlit run web/app.py" -WindowStyle Normal

Write-Host "Servers starting... Please wait a moment, then open http://localhost:8501"