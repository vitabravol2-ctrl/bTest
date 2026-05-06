from dataclasses import dataclass
from enum import Enum

from app.models import MarketTick


class FSMState(str, Enum):
    INIT = "INIT"
    IDLE = "IDLE"
    WATCHING = "WATCHING"
    DROP_DETECTED = "DROP_DETECTED"
    RECLAIM_WAIT = "RECLAIM_WAIT"
    ENTRY_READY = "ENTRY_READY"
    PAPER_POSITION = "PAPER_POSITION"
    EXIT = "EXIT"
    COOLDOWN = "COOLDOWN"


@dataclass(slots=True)
class FSMResult:
    state: str
    signal: str
    reason: str


class LiquidityGrabFSM:
    def __init__(self) -> None:
        self.state = FSMState.INIT

    def on_tick(self, _: MarketTick) -> FSMResult:
        if self.state == FSMState.INIT:
            self.state = FSMState.IDLE
        return FSMResult(
            state=self.state.value,
            signal="NO_SIGNAL",
            reason="core kernel only",
        )
