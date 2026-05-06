from __future__ import annotations

from dataclasses import dataclass

from app.signals import LiquidityGrabSignal

SIGNAL_GROUP_COOLDOWN_MS = 5000


@dataclass(slots=True)
class SignalQualitySnapshot:
    signal_id: int
    signal_group_id: int
    timestamp: int
    entry_price: float
    score: float
    phase: str
    reason_codes: list[str]
    setup_age_ms: int
    reclaim_hold_ms: int
    grade: str
    grouped: bool


class SignalQualityEngine:
    def __init__(self, signal_min_score: float) -> None:
        self.signal_min_score = float(signal_min_score)
        self._last_signal_ts = -1
        self._signal_id = 0
        self._group_id = 0
        self.raw_signal_count = 0
        self.grouped_signal_count = 0
        self.grade_counts = {"A": 0, "B": 0, "C": 0}

    def evaluate(self, signal: LiquidityGrabSignal, spread_ok: bool, reclaim_confirmed: bool) -> SignalQualitySnapshot | None:
        if not signal.detected:
            return None
        self._signal_id += 1
        self.raw_signal_count += 1
        grouped = self._last_signal_ts >= 0 and (signal.ts_ms - self._last_signal_ts) <= SIGNAL_GROUP_COOLDOWN_MS
        if not grouped:
            self._group_id += 1
            self.grouped_signal_count += 1
        self._last_signal_ts = signal.ts_ms
        grade = self._grade(signal.score, spread_ok=spread_ok, reclaim_confirmed=reclaim_confirmed)
        self.grade_counts[grade] = self.grade_counts.get(grade, 0) + 1
        return SignalQualitySnapshot(
            signal_id=self._signal_id,
            signal_group_id=self._group_id,
            timestamp=signal.ts_ms,
            entry_price=float(signal.trigger_price or 0.0),
            score=float(signal.score),
            phase=signal.phase,
            reason_codes=list(signal.reason_codes),
            setup_age_ms=int(signal.setup_age_ms),
            reclaim_hold_ms=int(signal.reclaim_hold_ms),
            grade=grade,
            grouped=grouped,
        )

    def _grade(self, score: float, *, spread_ok: bool, reclaim_confirmed: bool) -> str:
        if score >= 90.0 and spread_ok and reclaim_confirmed:
            return "A"
        if score >= 80.0:
            return "B"
        if score >= self.signal_min_score:
            return "C"
        return "C"
