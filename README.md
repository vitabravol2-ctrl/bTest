# bTest v0.3.2 — Detector Stabilization

bTest is a detector-focused prototype for BTCUSDT liquidity-grab analysis.

## Scope in v0.3.2
- No live trading.
- No API keys.
- No paper execution.
- No recorder/replay in this version.

## What is stabilized
- Detector now supports injectable time provider (`now_ms_provider`) for deterministic tests.
- Unit tests use `FakeClock` to drive reclaim hold/cooldown/timeout paths.
- Detector/FSM behavior around invalidation and recovery is hardened.

## Next milestone
- v0.4.0 is planned for Signal Recorder + Replay Dataset.
