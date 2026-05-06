import asyncio
import json
import time

import websockets
from PySide6.QtCore import QObject, Signal

from app.config import LOG_THROTTLE_MS, SYMBOL, WS_URL
from app.models import MarketTick


class MarketWSClient(QObject):
    tick_received = Signal(object)
    status_changed = Signal(str)
    error = Signal(str)

    def __init__(self, logger) -> None:
        super().__init__()
        self.logger = logger
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._last_log_ms = 0

    async def connect(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def disconnect(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        self.status_changed.emit("CONNECTING")
        self.logger.info("Connecting to Binance WS")
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
                self.status_changed.emit("CONNECTED")
                self.logger.info("Connected to Binance WS")
                while not self._stop_event.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    tick = self._parse_tick(raw)
                    if tick:
                        self.tick_received.emit(tick)
                        self._log_tick_throttled(tick)
        except Exception as exc:
            self.error.emit(str(exc))
            self.logger.exception("WS error: %s", exc)
        finally:
            self.status_changed.emit("DISCONNECTED")
            self.logger.info("Disconnected from Binance WS")

    def _parse_tick(self, raw: str) -> MarketTick | None:
        data = json.loads(raw)
        bid = float(data.get("b", 0.0))
        ask = float(data.get("a", 0.0))
        if bid <= 0 or ask <= 0:
            return None
        mid = (bid + ask) / 2.0
        spread_pct = ((ask - bid) / mid) * 100.0 if mid else 0.0
        return MarketTick(
            symbol=SYMBOL,
            bid=bid,
            ask=ask,
            bid_qty=float(data.get("B", 0.0)),
            ask_qty=float(data.get("A", 0.0)),
            mid=mid,
            spread_pct=spread_pct,
            ts_ms=int(time.time() * 1000),
        )

    def _log_tick_throttled(self, tick: MarketTick) -> None:
        now = tick.ts_ms
        if now - self._last_log_ms >= LOG_THROTTLE_MS:
            self._last_log_ms = now
            self.logger.info(
                "Tick %s bid=%.2f ask=%.2f spread=%.5f%%",
                tick.symbol,
                tick.bid,
                tick.ask,
                tick.spread_pct,
            )
