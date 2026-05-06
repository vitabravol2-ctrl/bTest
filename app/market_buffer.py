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

    def ticks_in_window(self, window_ms: int) -> list[MarketTick]:
        return self._window(window_ms)

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

    def price_change_pct(self, window_ms: int) -> float:
        window = self._window(window_ms)
        if len(window) < 2:
            return 0.0
        first = window[0].mid
        last = window[-1].mid
        if first == 0:
            return 0.0
        return (last - first) / first * 100.0

    def impulse_speed_pct_per_sec(self, window_ms: int) -> float:
        change_pct = self.price_change_pct(window_ms)
        seconds = window_ms / 1000.0
        if seconds <= 0:
            return 0.0
        return change_pct / seconds

    def spread_avg(self, window_ms: int) -> float:
        window = self._window(window_ms)
        if not window:
            return 0.0
        return sum(t.spread_pct for t in window) / len(window)

    def spread_max(self, window_ms: int) -> float:
        window = self._window(window_ms)
        if not window:
            return 0.0
        return max(t.spread_pct for t in window)

    def volatility_pct(self, window_ms: int) -> float:
        lo = self.low(window_ms)
        hi = self.high(window_ms)
        if lo is None or hi is None or lo <= 0:
            return 0.0
        return (hi - lo) / lo * 100.0

    def tick_rate(self, window_ms: int) -> float:
        window = self._window(window_ms)
        seconds = window_ms / 1000.0
        if seconds <= 0:
            return 0.0
        return len(window) / seconds

    def is_enough_data(self, window_ms: int, min_ticks: int) -> bool:
        return len(self._window(window_ms)) >= min_ticks
