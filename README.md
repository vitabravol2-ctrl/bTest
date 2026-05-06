# bTest v0.4.2 — Threshold Profiles + Config Panel

bTest is a detector-focused prototype for BTCUSDT liquidity-grab analysis.

## Scope in v0.4.2
- No live trading.
- No API keys.
- No paper execution.
- Recorder/replay flow remains supported.
- Detector logic is unchanged; only threshold configurability was added.

## Why threshold profiles were added
Real recordings showed that a fixed `MIN_GRAB_DROP_PCT=0.08` was too strict for many valid setups.
Profiles allow changing sensitivity without editing code.

## Available profiles
- **CONSERVATIVE**: drop 0.08, bounce 0.04, speed 0.01, mid trend 0.35, slow trend 0.60, score 70
- **BALANCED**: drop 0.04, bounce 0.02, speed 0.005, mid trend 0.30, slow trend 0.50, score 65
- **SENSITIVE**: drop 0.02, bounce 0.01, speed 0.002, mid trend 0.25, slow trend 0.40, score 60
- **DEBUG_ULTRA**: drop 0.01, bounce 0.005, speed 0.001, mid trend 0.20, slow trend 0.35, score 55

## What changed in v0.4.2
- Added `ThresholdProfile` and predefined profiles in `app/profiles.py`.
- `LiquidityGrabDetector` now supports `set_profile(...)` and uses active profile thresholds.
- Added GUI profile selector (QComboBox) and profile-change logging.
- Added compact profile/threshold display in Detector Radar.
- Recorder JSONL events now include `profile_name` and key threshold values.
- Added profile-focused detector tests.

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

## Next step
v0.4.3 — Session Analyzer / threshold calibration report.
