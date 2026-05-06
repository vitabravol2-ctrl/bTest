# bTest v0.1.0 — Core Kernel / BTCUSDT Liquidity Grab Bot

Desktop GUI-приложение (ядро) для будущей стратегии Liquidity Grab / Stop Hunt по BTCUSDT.

## Что реализовано в v0.1.0
- PySide6 GUI со статусами рынка и FSM.
- Подключение к публичному Binance WebSocket (`bookTicker`).
- Сбор и буферизация market ticks.
- Заглушка FSM без торговли.
- Логирование в GUI и `logs/app.log`.

## Установка
```bash
pip install -r requirements.txt
```

## Запуск
```bash
python main.py
```

## Важно
В версии v0.1.0 **нет торговли**:
- нет API keys
- нет live trading
- нет реальных сделок
