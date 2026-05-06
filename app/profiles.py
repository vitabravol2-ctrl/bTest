from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdProfile:
    name: str
    min_grab_drop_pct: float
    min_reclaim_bounce_pct: float
    min_impulse_speed_pct_per_sec: float
    max_trend_drop_mid_pct: float
    max_slow_trend_drop_pct: float
    signal_min_score: float


BASELINE = ThresholdProfile("BASELINE", 0.006, 0.003, 0.0005, 0.25, 0.40, 45)
PROFILES = {"BASELINE": BASELINE}


def get_profile(profile_name: str, custom_profiles: dict[str, ThresholdProfile] | None = None) -> ThresholdProfile:
    if custom_profiles and profile_name in custom_profiles:
        return custom_profiles[profile_name]
    return PROFILES.get(profile_name, BASELINE)
