from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ResearchState(str, Enum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    COLLECTING_DATA = "COLLECTING_DATA"
    WARMUP = "WARMUP"
    DETECTING_SETUPS = "DETECTING_SETUPS"
    ANALYZING_SESSION = "ANALYZING_SESSION"
    VALIDATING_CALIBRATION = "VALIDATING_CALIBRATION"
    DECISION = "DECISION"
    WAITING_FOR_ENTRY = "WAITING_FOR_ENTRY"
    ERROR = "ERROR"


@dataclass
class ResearchProgress:
    current_state: str = ResearchState.IDLE.value
    progress_pct: int = 0
    status_text: str = "Idle"
    ticks_collected: int = 0
    session_seconds: int = 0
    sweeps_found: int = 0
    near_signals_count: int = 0
    top_blocker: str = "none"
    suggested_action: str = "NONE"
    confidence: str = "LOW"
    last_error: str = ""


class AutoResearchPipeline:
    def __init__(self) -> None:
        self.progress = ResearchProgress()

    def start(self) -> None:
        self._set_state(ResearchState.CONNECTING, 5, "Connecting to market feed")

    def set_collecting(self) -> None:
        self._set_state(ResearchState.COLLECTING_DATA, 15, "Collecting market ticks")

    def set_warmup(self, ticks_collected: int, session_seconds: int) -> None:
        self.progress.ticks_collected = ticks_collected
        self.progress.session_seconds = session_seconds
        self._set_state(ResearchState.WARMUP, 30, "Warmup in progress")

    def set_detecting(self, sweeps_found: int, near_signals_count: int, top_blocker: str) -> None:
        self.progress.sweeps_found = sweeps_found
        self.progress.near_signals_count = near_signals_count
        self.progress.top_blocker = top_blocker
        self._set_state(ResearchState.DETECTING_SETUPS, 45, "Detecting setups")

    def set_analyzing(self) -> None:
        self._set_state(ResearchState.ANALYZING_SESSION, 65, "Analyzing recorded session")

    def set_validating(self) -> None:
        self._set_state(ResearchState.VALIDATING_CALIBRATION, 80, "Validating calibration before/after")

    def set_decision(self, suggested_action: str, confidence: str, status_text: str) -> None:
        self.progress.suggested_action = suggested_action
        self.progress.confidence = confidence
        self._set_state(ResearchState.DECISION, 92, status_text)

    def set_waiting_for_entry(self) -> None:
        self._set_state(ResearchState.WAITING_FOR_ENTRY, 100, "Detector waiting for valid signal")

    def set_error(self, message: str) -> None:
        self.progress.last_error = message
        self._set_state(ResearchState.ERROR, self.progress.progress_pct, "Research pipeline error")

    def _set_state(self, state: ResearchState, pct: int, text: str) -> None:
        self.progress.current_state = state.value
        self.progress.progress_pct = pct
        self.progress.status_text = text
