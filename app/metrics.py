from dataclasses import dataclass


@dataclass(slots=True)
class MarketMetrics:
    window_ms: int
    tick_count: int
    high: float
    low: float
    last_mid: float
    price_change_pct: float
    drop_pct: float
    bounce_pct: float
    impulse_speed_pct_per_sec: float
    spread_now_pct: float
    spread_avg_pct: float
    spread_max_pct: float
    volatility_pct: float
    tick_rate: float
    stale: bool
    enough_data: bool
