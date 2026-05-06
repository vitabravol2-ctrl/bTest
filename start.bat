@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Preparing venv
if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing requirements
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo [3/4] Running tests
pytest -q
if errorlevel 1 goto :error

echo [4/4] Starting app
python main.py
if errorlevel 1 goto :error

goto :eof

:error
echo.
echo Application exited with an error.
pause
