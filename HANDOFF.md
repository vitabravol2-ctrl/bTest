# bTest HANDOFF

## Version
v0.2.0

## What was implemented
- Добавлен модуль аналитики данных `DataAnalyzer` для подготовки рыночных сигналов без торговых действий.
- Добавлен `MarketMetrics` dataclass c набором метрик качества/динамики цены.
- Расширен `MarketBuffer` новыми методами окна: ticks, change, speed, spread avg/max, volatility, tick rate, enough-data check.
- Обновлён GUI: новый блок **Data Analyzer** с fast-метриками и статусом Data quality.
- Обновлён FSM: принимает `MarketMetrics` и возвращает state/signal/reason, без входа в сделки.
- Добавлены параметры конфигурации окон анализа и quality-фильтров.
- Добавлено throttled логирование summary анализа раз в 2 секунды.

## How to run
1. `pip install -r requirements.txt`
2. `python main.py`
3. Нажать `Connect` для Binance WS и наблюдать обновления Bid/Ask/метрик.

## Files changed
- app/analyzer.py
- app/metrics.py
- app/gui/main_window.py
- app/gui/widgets.py
- app/market_buffer.py
- app/strategy/liquidity_grab_fsm.py
- app/config.py
- README.md
- HANDOFF.md

## Metrics added
- `tick_count`, `high`, `low`, `last_mid`
- `price_change_pct`, `drop_pct`, `bounce_pct`, `impulse_speed_pct_per_sec`
- `spread_now_pct`, `spread_avg_pct`, `spread_max_pct`
- `volatility_pct`, `tick_rate`
- `stale`, `enough_data`

## Known limitations
- Торгового контура нет: FSM не открывает/закрывает позиции.
- Анализатор использует только live stream, без исторических свечей/ордербука L2.
- GUI показывает fast-окно, а mid/slow пока используются как подготовка под v0.3.0.
- Нет отдельной визуализации time-series графиков метрик.

## Next recommended step
v0.3.0 Liquidity Grab Detector:
- добавить detector паттернов drop→bounce/reclaim,
- согласовать fast/mid/slow условия,
- подготовить структуру trigger-сигналов для будущего execution модуля (всё ещё без live trading по умолчанию).
