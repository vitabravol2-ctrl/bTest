# bTest v0.3.0 — Liquidity Grab Detector / Signal Engine

Desktop GUI-приложение для анализа BTCUSDT и детекции **Liquidity Grab / Stop Hunt** сигналов (только сигнализация, без торговли).

## Что реализовано в v0.3.0
- Добавлен `LiquidityGrabDetector` с фазами:
  - `NO_SETUP`
  - `WATCHING_DROP`
  - `LIQUIDITY_SWEEP`
  - `RECLAIM_CONFIRMED`
  - `LONG_SIGNAL`
- Добавлен `LiquidityGrabSignal` dataclass для унифицированного сигнала detector-а.
- Добавлен scoring `0..100`:
  - drop strength (до 25)
  - bounce/reclaim (до 25)
  - speed/impulse (до 20)
  - spread quality (до 15)
  - anti-trend filter (до 15)
- Обновлён FSM: принимает `LiquidityGrabSignal` и отображает фазы detector-а (без сделок).
- Обновлён GUI:
  - новый блок **Liquidity Grab Detector**
  - расширенный **Strategy Status** (FSM State / Signal / Reason)
- Добавлено throttled detector logging summary каждые 2 секунды и отдельный лог при `LONG_SIGNAL_READY`.

## Как читать detector
- `phase` — текущая стадия паттерна.
- `score` — качество сигнала (0–100).
- `reason_codes` — почему сигнал заблокирован или подтверждён.
- `detected=true` и `side=LONG` только если пройдены hard-фильтры и `score >= SIGNAL_MIN_SCORE`.

## Reason codes
- `WAITING_DATA`
- `STALE_DATA`
- `HIGH_SPREAD`
- `DROP_TOO_SMALL`
- `BOUNCE_TOO_SMALL`
- `IMPULSE_TOO_SLOW`
- `MID_TREND_TOO_DANGEROUS`
- `SWEEP_FOUND`
- `RECLAIM_CONFIRMED`
- `LONG_SIGNAL_READY`

## Установка
```bash
pip install -r requirements.txt
```

## Запуск
```bash
python main.py
```

## Важно
В версии v0.3.0 **нет торговли**:
- нет API keys
- нет live trading
- нет реальных ордеров
- нет paper execution
- есть только detector сигнала + FSM + GUI отображение
