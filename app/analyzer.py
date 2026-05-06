from dataclasses import dataclass
import time

from app.market_buffer import MarketBuffer
from app.metrics import MarketMetrics


@dataclass(slots=True)
class AnalyzerConfig:
    fast_window_ms: int
    mid_window_ms: int
    slow_window_ms: int
    min_ticks_fast: int
    stale_after_ms: int


class DataAnalyzer:
    def __init__(self, config: AnalyzerConfig) -> None:
        self.config = config

    def analyze_window(self, buffer: MarketBuffer, window_ms: int, min_ticks: int) -> MarketMetrics:
        ticks = buffer.ticks_in_window(window_ms)
        last = buffer.last()
        if ticks:
            high = max(t.ask for t in ticks)
            low = min(t.bid for t in ticks)
            last_mid = ticks[-1].mid
        else:
            high = 0.0
            low = 0.0
            last_mid = 0.0

        now_ms = int(time.time() * 1000)
        stale = True if not last else buffer.is_stale(self.config.stale_after_ms, now_ms)
        return MarketMetrics(
            window_ms=window_ms,
            tick_count=len(ticks),
            high=high,
            low=low,
            last_mid=last_mid,
            price_change_pct=buffer.price_change_pct(window_ms),
            drop_pct=buffer.drop_pct(window_ms),
            bounce_pct=buffer.bounce_pct(window_ms),
            impulse_speed_pct_per_sec=buffer.impulse_speed_pct_per_sec(window_ms),
            spread_now_pct=(last.spread_pct if last else 0.0),
            spread_avg_pct=buffer.spread_avg(window_ms),
            spread_max_pct=buffer.spread_max(window_ms),
            volatility_pct=buffer.volatility_pct(window_ms),
            tick_rate=buffer.tick_rate(window_ms),
            stale=stale,
            enough_data=buffer.is_enough_data(window_ms, min_ticks),
        )

    def analyze(self, buffer: MarketBuffer) -> dict[str, MarketMetrics]:
        return {
            "fast": self.analyze_window(buffer, self.config.fast_window_ms, self.config.min_ticks_fast),
            "mid": self.analyze_window(buffer, self.config.mid_window_ms, max(self.config.min_ticks_fast, 8)),
            "slow": self.analyze_window(buffer, self.config.slow_window_ms, max(self.config.min_ticks_fast, 12)),
        }
