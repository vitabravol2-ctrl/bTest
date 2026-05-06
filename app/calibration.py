from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.profiles import ThresholdProfile


@dataclass(frozen=True)
class CalibrationSuggestion:
    name: str
    min_grab_drop_pct: float
    min_reclaim_bounce_pct: float
    min_impulse_speed_pct_per_sec: float
    max_trend_drop_mid_pct: float
    max_slow_trend_drop_pct: float
    signal_min_score: float
    reasons: list[str]
    runtime_params: dict[str, Any] | None = None

    def to_profile(self) -> ThresholdProfile:
        return ThresholdProfile(
            name=self.name,
            min_grab_drop_pct=self.min_grab_drop_pct,
            min_reclaim_bounce_pct=self.min_reclaim_bounce_pct,
            min_impulse_speed_pct_per_sec=self.min_impulse_speed_pct_per_sec,
            max_trend_drop_mid_pct=self.max_trend_drop_mid_pct,
            max_slow_trend_drop_pct=self.max_slow_trend_drop_pct,
            signal_min_score=self.signal_min_score,
        )
