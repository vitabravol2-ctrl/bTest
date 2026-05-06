from collections import deque
from typing import Deque

from app.models import MarketTick


class MarketBuffer:
    def __init__(self, maxlen: int = 1000) -> None:
        self._ticks: Deque[MarketTick] = deque(maxlen=maxlen)

    def add_tick(self, tick: MarketTick) -> None:
        self._ticks.append(tick)

    def last(self) -> MarketTick | None:
        return self._ticks[-1] if self._ticks else None

    def is_stale(self, max_age_ms: int, now_ms: int) -> bool:
        last = self.last()
        if not last:
            return True
        return now_ms - last.ts_ms > max_age_ms

    def _window(self, window_ms: int) -> list[MarketTick]:
        if not self._ticks:
            return []
        end_ts = self._ticks[-1].ts_ms
        start_ts = end_ts - window_ms
        return [t for t in self._ticks if t.ts_ms >= start_ts]

    def high(self, window_ms: int) -> float | None:
        window = self._window(window_ms)
        return max((t.ask for t in window), default=None)

    def low(self, window_ms: int) -> float | None:
        window = self._window(window_ms)
        return min((t.bid for t in window), default=None)

    def drop_pct(self, window_ms: int) -> float:
        hi = self.high(window_ms)
        last = self.last()
        if hi is None or not last or hi == 0:
            return 0.0
        return (hi - last.bid) / hi * 100.0

    def bounce_pct(self, window_ms: int) -> float:
        lo = self.low(window_ms)
        last = self.last()
        if lo is None or not last or lo == 0:
            return 0.0
        return (last.ask - lo) / lo * 100.0
