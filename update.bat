@echo off
setlocal
cd /d "%~dp0"

git pull

echo [1/4] Preparing venv
if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing requirements
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo [3/4] Compiling app
python -m compileall app main.py

echo [4/4] Running tests
pytest -q
pause
