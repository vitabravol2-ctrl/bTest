$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

git pull

Write-Host "[1/4] Preparing venv"
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

Write-Host "[2/4] Installing requirements"
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

Write-Host "[3/4] Compiling app"
python -m compileall app main.py

Write-Host "[4/4] Running tests"
pytest -q
Read-Host "Update complete. Press Enter to close"
