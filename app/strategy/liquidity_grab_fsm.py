from dataclasses import dataclass
from enum import Enum

from app.config import MAX_ALLOWED_SPREAD_PCT
from app.metrics import MarketMetrics


class FSMState(str, Enum):
    INIT = "INIT"
    IDLE = "IDLE"
    WATCHING = "WATCHING"


@dataclass(slots=True)
class FSMResult:
    state: str
    signal: str
    reason: str


class LiquidityGrabFSM:
    def __init__(self, max_allowed_spread_pct: float = MAX_ALLOWED_SPREAD_PCT) -> None:
        self.state = FSMState.INIT
        self.max_allowed_spread_pct = max_allowed_spread_pct

    def evaluate(self, metrics: MarketMetrics) -> FSMResult:
        if self.state == FSMState.INIT:
            self.state = FSMState.IDLE

        if not metrics.enough_data:
            return FSMResult(self.state.value, "DATA_WAITING", "Not enough ticks in fast window")
        if metrics.stale:
            return FSMResult(self.state.value, "DATA_STALE", "Last tick is stale")
        if metrics.spread_avg_pct > self.max_allowed_spread_pct:
            return FSMResult(self.state.value, "HIGH_SPREAD", "Spread above allowed threshold")

        self.state = FSMState.WATCHING
        return FSMResult(self.state.value, "WATCHING_MARKET", "Data quality good, monitoring only")
