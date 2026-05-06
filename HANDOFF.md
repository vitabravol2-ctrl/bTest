# bTest HANDOFF

## Version
v0.3.2

## Current status
Detector/FSM testability and timing behavior are stabilized with deterministic unit tests.

## What was fixed
- Added injectable detector time provider (`now_ms_provider`).
- Added explicit bounce hard-filter (`BOUNCE_TOO_SMALL`) before reclaim timer starts.
- Added invalidation cooldown guard with `INVALIDATION_COOLDOWN_MS` and reason code `INVALIDATION_COOLDOWN`.
- Updated FSM transitions so state can move out of `INVALIDATED` and enter `COOLDOWN` when signal disappears.

## Detector lifecycle
WATCHING_DROP -> LIQUIDITY_SWEEP -> RECLAIM_WAIT -> RECLAIM_CONFIRMED -> LONG_SIGNAL

Invalidation paths move detector to `INVALIDATED`, then cooldown gate applies before setup can restart.

## Config thresholds
See `app/config.py` for:
- `MIN_GRAB_DROP_PCT`
- `MIN_RECLAIM_BOUNCE_PCT`
- `RECLAIM_HOLD_MS`
- `RECLAIM_TIMEOUT_MS`
- `SETUP_MAX_AGE_MS`
- `INVALIDATION_COOLDOWN_MS`

## Tests
Detector tests cover waiting data, small drop, small bounce, reclaim hold, slow trend filter, new-low invalidation, high spread reset, invalidation cooldown, setup age invalidation, and reclaim timeout invalidation.

## Files changed
- `app/detector.py`
- `app/config.py`
- `app/strategy/liquidity_grab_fsm.py`
- `tests/test_detector.py`
- `README.md`
- `HANDOFF.md`

## Known limitations
- No execution engine/trading integration.
- No recorder/replay dataset tooling yet.

## Next recommended step
v0.4.0 — Signal Recorder + Replay Dataset
