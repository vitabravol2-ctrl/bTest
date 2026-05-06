# bTest HANDOFF

## Version
v0.4.4

## What was added
- Added offline calibration model `CalibrationSuggestion` with `to_profile()` in `app/calibration.py`.
- Extended `SessionAnalyzer` with `suggest_profile()` and report section `=== SUGGESTED CALIBRATED PROFILE ===`.
- GUI now stores latest suggestion, logs it after **ANALYZE SESSION**, and supports **APPLY CALIBRATION** for runtime detector profile switching to `CALIBRATED`.
- CLI `tools/analyze_session.py` now prints report containing suggested calibrated thresholds automatically.
- Added calibration tests covering empty data, p95 mapping, abs(speed), conversion to `ThresholdProfile`, and report text section.

## Known limitations
- Calibration suggestion is offline and heuristic-based; it does not optimize via backtesting.
- Suggested thresholds are not persisted to default `PROFILES`; they are runtime-only unless added manually.

## Next recommended step
- v0.4.5 Replay Timeline GUI OR v0.5.0 Paper Simulation
