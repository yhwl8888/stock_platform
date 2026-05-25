$env:PYTHONPATH = "D:\stock_platform"
$wdir = "D:\stock_platform"
python -m uvicorn api.main:app --port 8000 --host 0.0.0.0 2>&1 | Write-Host
