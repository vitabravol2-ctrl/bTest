# bTest HANDOFF

## Version
v0.4.2

## What changed
- Added `ThresholdProfile` model and predefined sets in `app/profiles.py`:
  - CONSERVATIVE
  - BALANCED
  - SENSITIVE
  - DEBUG_ULTRA
- Detector updates (`app/detector.py`):
  - default profile is CONSERVATIVE
  - `set_profile(profile)` API added
  - profile-based thresholds wired for drop/bounce/speed/trend/score checks
  - timing controls (`RECLAIM_HOLD_MS`, `SETUP_MAX_AGE_MS`, `RECLAIM_TIMEOUT_MS`) still come from config
- GUI updates (`app/gui/main_window.py`):
  - top-panel profile selector (QComboBox)
  - runtime profile switching via `detector.set_profile(...)`
  - explicit log line when profile changes
  - detector radar now shows active profile + drop/bounce/score thresholds
- Recorder updates (`app/recorder.py`):
  - JSONL event now includes `profile_name`
  - JSONL event includes key threshold snapshot:
    - `min_grab_drop_pct`
    - `min_reclaim_bounce_pct`
    - `signal_min_score`
- Tests (`tests/test_detector.py`):
  - default profile test
  - sensitive profile small-drop behavior
  - profile switch threshold behavior
  - debug ultra sweep entry with small drop
  - legacy tests still passing

## Non-goals reaffirmed
- No trading/execution engine.
- No API keys.
- No paper execution.

## Next recommended step
v0.4.3 — Session Analyzer / threshold calibration report.
