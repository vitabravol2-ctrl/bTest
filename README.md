# bTest v0.4.4 — Session Analyzer / Threshold Calibration Report

bTest is a detector-focused prototype for BTCUSDT liquidity-grab analysis.

## Scope in v0.4.4
- No live trading.
- No API keys.
- No paper execution.
- Recorder/replay flow remains supported.
- Detector logic is unchanged; only offline session analysis was added.

## New in v0.4.4: Session Analyzer
Analyze recorded `session_*.jsonl` files to understand:
- why a signal did not appear
- which conditions block most often
- what profile was used most
- what threshold calibration hints the session suggests

### Analyze via GUI
1. Start app (`python main.py`).
2. Click **ANALYZE SESSION**.
3. Select a JSONL file from `data/sessions`.
4. The app saves `session_xxx_report.txt` рядом с JSONL и пишет в лог:
   - `total_events`
   - `max_score`
   - `detected_count`
   - top blocker
   - report path

### Analyze via CLI
```bash
python tools/analyze_session.py data/sessions/session_xxx.jsonl
```

The command prints a text report to console and saves:
- `data/sessions/session_xxx_report.txt`

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
v0.4.4 — Replay Timeline GUI / calibration presets.


## Calibration flow (GUI)
1. Click **ANALYZE SESSION** and select `session_*.jsonl`.
2. Analyzer builds `CALIBRATED` suggestion from p95 drop/bounce/speed plus near-signal blockers.
3. Log shows: `Suggested CALIBRATED profile: drop=X bounce=Y speed=Z score=S`.
4. Click **APPLY CALIBRATION** to apply suggested thresholds to active detector profile.
5. Active profile label switches to `CALIBRATED` (profile combo may remain unchanged).


## v0.4.6 — Signal Quality Engine

В v0.4.6 добавлен слой качества сигналов, чтобы поток raw `LONG_SIGNAL` превращался в ограниченный набор market events.

- Введены grades: `A_PLUS`, `A`, `B`, `C`, `TRASH`.
- Добавлен антиспам-кластеринг: один liquidity grab => один market event; дубликаты подавляются.
- Добавлен signal decay по возрасту setup (`setup_age_ms`).
- Добавлены reason codes и component-based quality score для объяснимости.
- Raw `LONG_SIGNAL` больше не равен торговому сигналу: это только вход в pipeline качества.
- Live trading по-прежнему запрещён: v0.4.6 не отправляет реальные ордера, не использует API keys и не делает position sizing.

## v0.4.6.1 — Analyzer Math Fix + Post-Signal Performance

- Исправлена логика PS Reclaim rate: раньше смешивались `ticks/events` и `unique setups`, что могло давать значения >100%.
- Теперь post-sweep метрики разделены на тик-счётчики и уникальные сетапы, а `reclaim_success_rate_pct`/`signal_success_rate_pct` считаются только как `unique/unique`.
- Добавлен offline post-signal analysis по session jsonl: 1s/3s/5s/10s return, max favorable/adverse за 10s, агрегация по grade.
- Это по-прежнему аналитика (post-session), а не real paper/live execution.
- Этап v0.5.0 остаётся следующим и не реализуется в этой версии.

## v0.4.6.2 — Persist Post-Signal Metrics + Baseline Profile Simplification

- Profile playground removed in favor of one stable `BASELINE` profile for comparable session statistics.
- Analyzer now writes enriched copy of session JSONL (`*_enriched.jsonl`) with persisted post-signal metrics for each event.
- This improves repeatability of research and prepares data interfaces for v0.5.0 Real Paper Trading Engine.
- This release is **not live trading**: no real orders, no Binance keys, no position sizing, no risk execution.
- Next stage (v0.5.0): integrate a dedicated Real Paper Trading Engine on top of enriched analytics.
