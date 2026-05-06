# bTest v0.2.0 — Data Analyzer / BTCUSDT Liquidity Metrics

Desktop GUI-приложение для анализа рыночных данных BTCUSDT под будущий Liquidity Grab / Stop Hunt алгоритм.

## Что реализовано в v0.2.0
- Расширенный `MarketBuffer` с метриками окна (speed/volatility/spread/tick rate/data sufficiency).
- Новый `MarketMetrics` dataclass для стандартизированного набора метрик.
- Новый `DataAnalyzer` с multi-window анализом: fast (10s), mid (30s), slow (120s).
- Обновлён GUI: блок **Data Analyzer** с ключевыми метриками и статусом качества данных.
- FSM обновлён: принимает метрики и отдаёт сигналы качества данных (без торговли).
- Throttled logging summary анализа раз в 2 секунды.

## Сигналы FSM v0.2.0
- `NO_SIGNAL` (дефолт при старте)
- `DATA_WAITING`
- `DATA_STALE`
- `HIGH_SPREAD`
- `WATCHING_MARKET`

## Установка
```bash
pip install -r requirements.txt
```

## Запуск
```bash
python main.py
```

## Важно
В версии v0.2.0 **нет торговли**:
- нет API keys
- нет live trading
- нет реальных сделок
- нет paper trading
- FSM только анализирует данные и возвращает статусы/сигналы
