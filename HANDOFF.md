# bTest HANDOFF

## Version
v0.4.0

## What changed
- Added `SignalRecorder` (`app/recorder.py`):
  - `start_session()`
  - `stop_session()`
  - `record_tick(tick, metrics, signal, fsm_state)`
  - `flush_to_file()`
- Recording format: JSONL events with market fields, analyzer metrics, detector fields, FSM state, and reason codes.
- Added memory/IO guardrails:
  - max in-memory buffer: 5000 events
  - auto flush interval: every 2 seconds
- Added replay module `ReplayEngine` (`app/replay.py`) with:
  - `load_file(path)`
  - `play(speed=1.0)`
  - `pause()`
  - `step()`
- Integrated recorder in GUI:
  - app connect → `start_session()`
  - each tick → `record_tick(...)`
  - close/disconnect → `stop_session()`
- Added top-panel `REC ●` LED indicator:
  - green = recording
  - gray = off
- Added `LOAD REPLAY` GUI button:
  - opens file picker for `data/sessions/*.jsonl`
  - loads file into replay engine and logs result
- Added `data/sessions/.gitkeep` to preserve dataset folder in repo.
- Updated README with recording/replay usage notes.

## GUI layout
- Left: market snapshot (symbol, last/bid/ask, spread, tick age/rate).
- Center: detector radar (phase, score, side, signal, reason, reason codes, timers, invalid reason).
- Right: analyzer values + FSM state.
- Status color mapping implemented for connection/data quality/phase/signal cues.

## Known limitations
- No execution engine/trading integration.
- Replay engine currently logs events to console only (no full GUI playback pipeline yet).
- GUI is optimized for 16:9 desktop layouts and may require resizing on smaller displays.

## Next recommended step
v0.4.x — enrich replay controls and visual timeline integration.
