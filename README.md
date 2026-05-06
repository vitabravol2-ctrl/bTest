# bTest v0.3.4 — Real Cockpit Indicators GUI + Launcher/Updater

bTest is a detector-focused prototype for BTCUSDT liquidity-grab analysis.

## Scope in v0.3.4
- No live trading.
- No API keys.
- No paper execution.
- No recorder/replay in this version.

## What changed in v0.3.4
- GUI redesigned into a compact cockpit dashboard with top LED indicator strip and 3-column radar layout.
- Detector/FSM/analyzer/market fields are visible on a single 1600x900 screen without scrolling.
- Added Windows launcher and updater scripts (`start.bat`, `update.bat`, `start.ps1`, `update.ps1`).

## Windows quick start
1. Double click `start.bat`.
2. For project updates, run `update.bat`.

## Manual start commands
```bash
python -m venv .venv
# Windows CMD
.venv\Scripts\activate
# or PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Manual update commands
```bash
git pull
python -m venv .venv
# activate venv first
pip install -r requirements.txt
python -m compileall app main.py
pytest -q
```

## Next milestone
- v0.4.0 is planned for Signal Recorder + Replay Dataset.


### v0.3.4 GUI upgrades
- Real cockpit indicators with dedicated LED status panel: WS, DATA, DROP, SWEEP, RECLAIM, SIGNAL, BLOCK.
- Detector radar now includes prominent PHASE/SCORE, score progress bar (0-100), signal lamp text, and compact reason/reason-codes presentation.
- Layout compacted to remove excess empty space in cards and optimize density for 1600x900.
