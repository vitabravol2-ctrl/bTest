$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "[1/4] Preparing venv"
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

Write-Host "[2/4] Installing requirements"
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

Write-Host "[3/4] Running tests"
pytest -q

try {
    Write-Host "[4/4] Starting app"
    python main.py
}
catch {
    Write-Host "`nApplication exited with an error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to close"
}
