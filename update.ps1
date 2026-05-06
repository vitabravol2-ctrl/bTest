$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

git pull
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall app main.py
pytest -q
Read-Host "Update complete. Press Enter to close"
