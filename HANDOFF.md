# bTest HANDOFF

## Version
v0.3.0

## What was implemented
- Добавлен `LiquidityGrabSignal` dataclass (`app/signals.py`) как единый формат detector-сигнала.
- Добавлен `LiquidityGrabDetector` (`app/detector.py`) с реальной логикой LONG stop hunt.
- Реализованы фазы detector-а: `NO_SETUP` → `WATCHING_DROP` → `LIQUIDITY_SWEEP` → `RECLAIM_CONFIRMED` → `LONG_SIGNAL`.
- Реализованы hard-фильтры: data sufficiency, stale check, spread check, min drop/bounce, impulse speed, mid trend risk, reclaim hold.
- Добавлен score 0–100 с весами (drop/bounce/speed/spread/anti-trend).
- Обновлён FSM (`app/strategy/liquidity_grab_fsm.py`) — теперь принимает `LiquidityGrabSignal` и показывает состояния detector-а без сделок.
- Обновлён GUI (`app/gui/main_window.py`) новым блоком **Liquidity Grab Detector** и расширенным Strategy Status.
- Добавлены detector thresholds в `app/config.py`.
- Добавлено detector summary логирование раз в 2 секунды и отдельный warning при `LONG_SIGNAL_READY`.

## Detector logic (LONG stop hunt)
Основной сценарий:
1. Проверка достаточности fast/mid данных.
2. Отсев stale и высокого spread.
3. Фиксация sweep при достаточном падении (drop).
4. Подтверждение reclaim через bounce + возврат цены выше reclaim-level.
5. Проверка impulse speed, anti-trend (mid drop), удержания reclaim (`RECLAIM_HOLD_MS`) и отсутствия нового low.
6. Если `score >= SIGNAL_MIN_SCORE` и все hard-фильтры пройдены — `detected=true`, `side=LONG`, `phase=LONG_SIGNAL`.

## Config thresholds
- `MIN_GRAB_DROP_PCT = 0.08`
- `MIN_RECLAIM_BOUNCE_PCT = 0.04`
- `MIN_IMPULSE_SPEED_PCT_PER_SEC = 0.01`
- `MAX_TREND_DROP_MID_PCT = 0.35`
- `RECLAIM_HOLD_MS = 1500`
- `SIGNAL_MIN_SCORE = 70.0`
- `DETECTOR_LOG_INTERVAL_MS = 2000`

## Files changed
- app/detector.py
- app/signals.py
- app/strategy/liquidity_grab_fsm.py
- app/gui/main_window.py
- app/gui/widgets.py
- app/config.py
- README.md
- HANDOFF.md

## Known limitations
- Торгового контура всё ещё нет (и намеренно): сигнал только отображается.
- Detector сфокусирован на LONG stop-hunt сценарии; SHORT ветка не реализована.
- Валидация на исторических dataset/replay ещё не встроена.

## Next recommended step
v0.4.0: **Signal Recorder + Replay Dataset**
- записывать поток ticks и detector snapshots,
- прогонять replay для калибровки thresholds/score,
- формировать baseline precision/false-positive метрик до любых execution-фич.
