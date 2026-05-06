from dataclasses import dataclass


@dataclass(slots=True)
class MarketTick:
    symbol: str
    bid: float
    ask: float
    bid_qty: float
    ask_qty: float
    mid: float
    spread_pct: float
    ts_ms: int
    source: str = "WS"
