@echo off
setlocal
cd /d "%~dp0"

git pull
if not exist .venv (
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall app main.py
pytest -q
pause
