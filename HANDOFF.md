# HANDOFF

## Version
v0.3.1

## What was fixed
- Stabilized detector sweep/reclaim lifecycle to avoid false positives from sweep-low overwrite.
- Reclaim target now uses `sweep_low * (1 + MIN_RECLAIM_BOUNCE_PCT / 100)`.
- Drop speed validation now confirms downward move only (`drop_pct / fast_window_sec`, no `abs`).
- Added reset/invalidation flow and explicit reason codes for setup aging, reclaim timeout, slow-trend danger, and reclaim invalidation.
- Expanded FSM mapping to include invalidated/reclaim phases and controlled cooldown behavior.
- Extended GUI detector panel with setup age, reclaim hold, and last invalid reason.

## Detector lifecycle
NO_SETUP -> WATCHING_DROP -> LIQUIDITY_SWEEP -> RECLAIM_WAIT -> RECLAIM_CONFIRMED -> LONG_SIGNAL

Invalidation path:
- INVALIDATED on stale/high spread/dangerous trend/reclaim timeout/setup too old/new low after reclaim.

## Tests added
- `tests/test_detector.py`
  - test_waiting_data_no_signal
  - test_drop_too_small_no_signal
  - test_sweep_then_reclaim_long_signal
  - test_slow_trend_blocks_signal
  - test_new_low_after_reclaim_invalidates
  - test_high_spread_resets_setup

## Known limitations
- Tests are unit-level and do not emulate full WS timing dynamics.
- Reclaim hold timing is still wall-clock dependent in detector runtime.

## Next recommended step
v0.4.0 — Signal Recorder + Replay Dataset
