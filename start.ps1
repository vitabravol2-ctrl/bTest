$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

try {
    python main.py
}
catch {
    Write-Host "`nApplication exited with an error:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to close"
}
