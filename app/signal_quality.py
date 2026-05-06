from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.signals import LiquidityGrabSignal

SIGNAL_CLUSTER_WINDOW_MS = 30_000
SIGNAL_COOLDOWN_MS = 15_000
MAX_SIGNALS_PER_CLUSTER = 1


class SignalQualityGrade(StrEnum):
    A_PLUS = "A_PLUS"
    A = "A"
    B = "B"
    C = "C"
    TRASH = "TRASH"


@dataclass(slots=True)
class SignalQualityResult:
    signal_id: int
    signal_cluster_id: int
    grade: str
    quality_score: float
    reason_codes: list[str]
    components: dict[str, float]
    is_new_market_event: bool
    is_duplicate_signal: bool


class SignalQualityEngine:
    def __init__(self, signal_min_score: float) -> None:
        self.signal_min_score = float(signal_min_score)
        self._last_signal_ts = -1
        self._signal_id = 0
        self._cluster_id = 0
        self._cluster_signals = 0
        self.raw_signal_count = 0
        self.market_events_count = 0
        self.grouped_signal_count = 0
        self.duplicate_signals_suppressed = 0
        self.grade_counts = {g.value: 0 for g in SignalQualityGrade}

    def evaluate(self, signal: LiquidityGrabSignal, spread_ok: bool, reclaim_confirmed: bool, stale: bool = False) -> SignalQualityResult | None:
        if not signal.detected:
            return None
        self.raw_signal_count += 1
        self._signal_id += 1

        dt = signal.ts_ms - self._last_signal_ts if self._last_signal_ts >= 0 else 10**9
        new_cluster = dt > SIGNAL_CLUSTER_WINDOW_MS
        cooldown_violation = dt <= SIGNAL_COOLDOWN_MS
        if new_cluster:
            self._cluster_id += 1
            self._cluster_signals = 0
            self.market_events_count += 1
            self.grouped_signal_count += 1

        self._cluster_signals += 1
        duplicate = cooldown_violation or self._cluster_signals > MAX_SIGNALS_PER_CLUSTER
        if duplicate:
            self.duplicate_signals_suppressed += 1
        self._last_signal_ts = signal.ts_ms

        components = self._components(signal, spread_ok=spread_ok)
        score = max(0.0, min(100.0, sum(components.values()) / len(components)))
        reasons = []
        if stale:
            reasons.append('stale_data')
        if not spread_ok:
            reasons.append('high_spread')
        if signal.setup_age_ms > 7000:
            reasons.append('setup_too_old')
        elif signal.setup_age_ms > 3000:
            reasons.append('setup_age_penalty')
        if signal.reclaim_distance_pct < 0:
            reasons.append('weak_reclaim')
        if not signal.bounce_ok_effective:
            reasons.append('weak_bounce')
        if duplicate:
            reasons.append('duplicate_signal')

        grade = self._grade(signal, score, stale=stale, spread_ok=spread_ok, reclaim_confirmed=reclaim_confirmed, duplicate=duplicate)
        self.grade_counts[grade.value] += 1
        return SignalQualityResult(self._signal_id, self._cluster_id, grade.value, score, reasons, components, new_cluster, duplicate)

    def _components(self, signal: LiquidityGrabSignal, *, spread_ok: bool) -> dict[str, float]:
        freshness = 100.0 if signal.setup_age_ms <= 3000 else (70.0 if signal.setup_age_ms <= 7000 else 20.0)
        return {
            'sweep_depth_quality': max(0.0, min(100.0, signal.score)),
            'bounce_quality': 100.0 if signal.bounce_ok_effective else 35.0,
            'reclaim_strength': 100.0 if signal.reclaim_distance_pct >= 0 else 20.0,
            'hold_quality': 100.0 if signal.reclaim_hold_ms >= signal.effective_hold_ms else 40.0,
            'speed_quality': max(0.0, min(100.0, signal.score)),
            'spread_safety': 100.0 if spread_ok else 10.0,
            'trend_safety': 100.0 if bool((signal.debug or {}).get('slow_trend_ok', True)) else 40.0,
            'freshness_quality': freshness,
        }

    def _grade(self, signal: LiquidityGrabSignal, score: float, *, stale: bool, spread_ok: bool, reclaim_confirmed: bool, duplicate: bool) -> SignalQualityGrade:
        bounce_ok = bool(getattr(signal, "bounce_ok_effective", True))
        reclaim_distance = float(getattr(signal, "reclaim_distance_pct", 0.0))
        if stale or not spread_ok or duplicate or signal.setup_age_ms > 7000 or reclaim_distance < 0:
            return SignalQualityGrade.TRASH
        if signal.score >= 90 and reclaim_distance >= 0 and bounce_ok and signal.reclaim_hold_ms >= signal.effective_hold_ms and signal.setup_age_ms <= 5000:
            return SignalQualityGrade.A_PLUS
        if signal.score >= 90 and spread_ok:
            return SignalQualityGrade.A
        if signal.score >= 80 and reclaim_confirmed and signal.reclaim_hold_ms >= signal.effective_hold_ms and signal.setup_age_ms <= 7000:
            return SignalQualityGrade.A
        if signal.score >= 70:
            return SignalQualityGrade.B
        if signal.score >= 55:
            return SignalQualityGrade.C
        if score >= self.signal_min_score:
            return SignalQualityGrade.C
        return SignalQualityGrade.TRASH
