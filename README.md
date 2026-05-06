# bTest v0.4.0 — Signal Recorder + Replay Dataset

bTest is a detector-focused prototype for BTCUSDT liquidity-grab analysis.

## Scope in v0.4.0
- No live trading.
- No API keys.
- No paper execution.
- Detector logic is unchanged (only data recording + replay tools added).

## What changed in v0.4.0
- Added `SignalRecorder` (`app/recorder.py`) with JSONL session recording.
- Added `ReplayEngine` (`app/replay.py`) to load/play/pause/step session files (console log output).
- Added `data/sessions/` storage with `session_YYYYMMDD_HHMMSS.jsonl` naming.
- Integrated recorder into GUI lifecycle (connect/start, tick/record, close/stop).
- Added REC ● indicator lamp (green=recording, gray=off).
- Added `LOAD REPLAY` button to open a JSONL replay file and log load status.

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

## Recordings location
- Session files are saved in `data/sessions/`.
- File format: JSONL, one event per line.
- Filename format: `session_YYYYMMDD_HHMMSS.jsonl`.

## Replay usage (basic)
1. Start GUI: `python main.py`.
2. Click `LOAD REPLAY`.
3. Select a file from `data/sessions/`.
4. The app logs loaded file path and event count; replay engine currently logs playback to console only.


### v0.3.4 GUI upgrades
- Real cockpit indicators with dedicated LED status panel: WS, DATA, DROP, SWEEP, RECLAIM, SIGNAL, BLOCK.
- Detector radar now includes prominent PHASE/SCORE, score progress bar (0-100), signal lamp text, and compact reason/reason-codes presentation.
- Layout compacted to remove excess empty space in cards and optimize density for 1600x900.
