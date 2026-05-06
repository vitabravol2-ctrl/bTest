# bTest HANDOFF

## Version
v0.1.0

## What was implemented
- Создан каркас desktop GUI на PySide6 с блоками Market Status, Strategy Status и лог-панелью.
- Добавлен WebSocket клиент Binance public stream для BTCUSDT `bookTicker`.
- Реализован `MarketTick` dataclass.
- Реализован `MarketBuffer` (max 1000) и базовые вычисления high/low/drop/bounce.
- Реализован placeholder FSM (`LiquidityGrabFSM`) без торговли.
- Добавлено логирование в GUI и файл `logs/app.log` с throttling тиков.
- Добавлены скрипты запуска и документация.

## How to run
1. `pip install -r requirements.txt`
2. `python main.py`

## Files changed
- main.py
- requirements.txt
- README.md
- HANDOFF.md
- run.bat
- run.ps1
- app/*
- app/strategy/*
- app/gui/*
- data/.gitkeep
- logs/.gitkeep

## Current architecture
- `app/config.py`: константы и пути.
- `app/models.py`: модели данных (`MarketTick`).
- `app/market_ws.py`: async WS клиент Binance.
- `app/market_buffer.py`: кольцевой буфер тиков и метрики.
- `app/strategy/liquidity_grab_fsm.py`: FSM placeholder.
- `app/gui/main_window.py`: основное GUI окно и интеграция компонентов.
- `app/logger.py`: файл+GUI логирование.

## Known limitations
- Нет real/paper execution, только сигнал-заглушка.
- Нет восстановления с backoff/reconnect policy.
- Интеграция asyncio + Qt выполнена через polling loop.

## Next recommended step
v0.2.0 Data Analyzer
