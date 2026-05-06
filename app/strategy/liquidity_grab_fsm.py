from dataclasses import dataclass
from enum import Enum

from app.signals import LiquidityGrabSignal


class FSMState(str, Enum):
    IDLE = "IDLE"
    WATCHING_DROP = "WATCHING_DROP"
    SWEEP_DETECTED = "SWEEP_DETECTED"
    RECLAIM_WAIT = "RECLAIM_WAIT"
    RECLAIM_CONFIRMED = "RECLAIM_CONFIRMED"
    SIGNAL_READY = "SIGNAL_READY"
    INVALIDATED = "INVALIDATED"
    COOLDOWN = "COOLDOWN"


@dataclass(slots=True)
class FSMResult:
    state: str
    signal: str
    reason: str


class LiquidityGrabFSM:
    def __init__(self) -> None:
        self.state = FSMState.IDLE

    def evaluate(self, signal: LiquidityGrabSignal) -> FSMResult:
        prev_state = self.state
        if signal.detected:
            self.state = FSMState.SIGNAL_READY
            return FSMResult(self.state.value, "LONG_SIGNAL", signal.human_reason)

        if signal.phase == "INVALIDATED":
            self.state = FSMState.INVALIDATED
        elif signal.phase == "WATCHING_DROP":
            if prev_state == FSMState.SIGNAL_READY:
                self.state = FSMState.COOLDOWN
            else:
                self.state = FSMState.WATCHING_DROP
        elif signal.phase == "LIQUIDITY_SWEEP":
            self.state = FSMState.SWEEP_DETECTED
        elif signal.phase == "RECLAIM_WAIT":
            self.state = FSMState.RECLAIM_WAIT
        elif signal.phase == "RECLAIM_CONFIRMED":
            self.state = FSMState.RECLAIM_CONFIRMED
        elif signal.phase == "NO_SETUP":
            self.state = FSMState.IDLE

        return FSMResult(self.state.value, "NO_SIGNAL", signal.human_reason)
