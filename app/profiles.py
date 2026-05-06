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


CONSERVATIVE = ThresholdProfile(
    name="CONSERVATIVE",
    min_grab_drop_pct=0.08,
    min_reclaim_bounce_pct=0.04,
    min_impulse_speed_pct_per_sec=0.01,
    max_trend_drop_mid_pct=0.35,
    max_slow_trend_drop_pct=0.60,
    signal_min_score=70,
)

BALANCED = ThresholdProfile(
    name="BALANCED",
    min_grab_drop_pct=0.04,
    min_reclaim_bounce_pct=0.02,
    min_impulse_speed_pct_per_sec=0.005,
    max_trend_drop_mid_pct=0.30,
    max_slow_trend_drop_pct=0.50,
    signal_min_score=65,
)

SENSITIVE = ThresholdProfile(
    name="SENSITIVE",
    min_grab_drop_pct=0.02,
    min_reclaim_bounce_pct=0.01,
    min_impulse_speed_pct_per_sec=0.002,
    max_trend_drop_mid_pct=0.25,
    max_slow_trend_drop_pct=0.40,
    signal_min_score=60,
)

DEBUG_ULTRA = ThresholdProfile(
    name="DEBUG_ULTRA",
    min_grab_drop_pct=0.01,
    min_reclaim_bounce_pct=0.005,
    min_impulse_speed_pct_per_sec=0.001,
    max_trend_drop_mid_pct=0.20,
    max_slow_trend_drop_pct=0.35,
    signal_min_score=55,
)

CUSTOM = ThresholdProfile(
    name="CUSTOM",
    min_grab_drop_pct=0.01,
    min_reclaim_bounce_pct=0.005,
    min_impulse_speed_pct_per_sec=0.001,
    max_trend_drop_mid_pct=0.20,
    max_slow_trend_drop_pct=0.35,
    signal_min_score=55,
)
CUSTOM_EXTREME_RESEARCH = ThresholdProfile(
    name="CUSTOM_EXTREME_RESEARCH",
    min_grab_drop_pct=0.006,
    min_reclaim_bounce_pct=0.003,
    min_impulse_speed_pct_per_sec=0.0005,
    max_trend_drop_mid_pct=0.250,
    max_slow_trend_drop_pct=0.400,
    signal_min_score=45,
)

PROFILES = {profile.name: profile for profile in (CONSERVATIVE, BALANCED, SENSITIVE, DEBUG_ULTRA, CUSTOM, CUSTOM_EXTREME_RESEARCH)}


def get_profile(profile_name: str, custom_profiles: dict[str, ThresholdProfile] | None = None) -> ThresholdProfile:
    if custom_profiles and profile_name in custom_profiles:
        return custom_profiles[profile_name]
    return PROFILES[profile_name]
