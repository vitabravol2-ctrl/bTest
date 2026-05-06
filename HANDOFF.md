# bTest HANDOFF

## Version
v0.3.4

## What changed
- Rebuilt GUI to cockpit/trading-dashboard style with:
  - Top app header and LED strip (WS, DATA, DROP, SWEEP, RECLAIM, SIGNAL, BLOCK).
  - Three fixed-width columns: MARKET, DETECTOR RADAR, ANALYZER.
  - Compact bottom log panel with controlled height.
- Added helper GUI methods:
  - `_make_card(title)`
  - `_make_value_label(size=...)`
  - `_set_badge(label, text, status)`
- Added launcher/update scripts for Windows:
  - `start.bat`
  - `update.bat`
  - `start.ps1`
  - `update.ps1`
- README updated with quick start and manual commands.

## GUI layout
- Left: market snapshot (symbol, last/bid/ask, spread, tick age/rate).
- Center: detector radar (phase, score, side, signal, reason, reason codes, timers, invalid reason).
- Right: analyzer values + FSM state.
- Status color mapping implemented for connection/data quality/phase/signal cues.

## Known limitations
- No execution engine/trading integration.
- No recorder/replay dataset tooling yet.
- GUI is optimized for 16:9 desktop layouts and may require resizing on smaller displays.

## Next recommended step
v0.4.0 — Signal Recorder + Replay Dataset

- Added detector score progress bar and compact cockpit card spacing to reduce empty zones.
