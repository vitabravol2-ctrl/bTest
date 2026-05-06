from app.config import (
    INVALIDATION_COOLDOWN_MS,
    RECLAIM_HOLD_MS,
    RECLAIM_TIMEOUT_MS,
    SETUP_MAX_AGE_MS,
)
from app.detector import LiquidityGrabDetector
from app.market_buffer import MarketBuffer
from app.metrics import MarketMetrics
from app.models import MarketTick
from app.profiles import CONSERVATIVE, DEBUG_ULTRA, SENSITIVE


class FakeClock:
    def __init__(self, now: int = 1_000_000) -> None:
        self.now = now

    def __call__(self) -> int:
        return self.now

    def advance(self, ms: int) -> None:
        self.now += ms


def mt(drop=0.0, bounce=0.0, spread=0.01, stale=False, enough=True, low=99.0, last_mid=100.0):
    return MarketMetrics(
        window_ms=10_000,
        tick_count=10,
        high=101.0,
        low=low,
        last_mid=last_mid,
        price_change_pct=0.0,
        drop_pct=drop,
        bounce_pct=bounce,
        impulse_speed_pct_per_sec=0.0,
        spread_now_pct=spread,
        spread_avg_pct=spread,
        spread_max_pct=spread,
        volatility_pct=0.0,
        tick_rate=2.0,
        stale=stale,
        enough_data=enough,
    )


def buf(bid=100.0, ask=100.1):
    b = MarketBuffer()
    b.add_tick(MarketTick("BTCUSDT", bid, ask, 1, 1, (bid + ask) / 2, (ask - bid) / ((ask + bid) / 2) * 100, 1))
    return b


def test_waiting_data_no_signal():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    s = d.detect(mt(enough=False), mt(), mt(), buf())
    assert not s.detected
    assert "WAITING_DATA" in s.reason_codes


def test_default_profile_is_conservative():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    assert d.profile == CONSERVATIVE


def test_drop_too_small_no_signal():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    s = d.detect(mt(drop=0.01), mt(), mt(), buf())
    assert not s.detected
    assert s.phase == "WATCHING_DROP"


def test_bounce_too_small_blocks_reclaim():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    s = d.detect(mt(drop=0.2, bounce=0.01, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert not s.detected
    assert "BOUNCE_TOO_SMALL" in s.reason_codes
    assert s.phase in {"LIQUIDITY_SWEEP", "RECLAIM_WAIT"}
    assert s.reclaim_hold_ms == 0


def test_sweep_then_reclaim_hold_then_long_signal():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    b = buf(bid=100.0, ask=100.2)
    s1 = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert not s1.detected
    clock.advance(RECLAIM_HOLD_MS - 100)
    s2 = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert not s2.detected
    clock.advance(200)
    s3 = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert s3.detected is True
    assert s3.side == "LONG"
    assert s3.phase == "LONG_SIGNAL"
    assert "LONG_SIGNAL_READY" in s3.reason_codes
    assert s3.score >= d.profile.signal_min_score


def test_sensitive_profile_allows_smaller_drop():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    d.set_profile(SENSITIVE)
    s = d.detect(mt(drop=0.03, bounce=0.02), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert "DROP_TOO_SMALL" not in s.reason_codes


def test_profile_switch_changes_drop_threshold():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    s1 = d.detect(mt(drop=0.03), mt(drop=0.1), mt(drop=0.1), buf())
    assert "DROP_TOO_SMALL" in s1.reason_codes
    d.set_profile(SENSITIVE)
    s2 = d.detect(mt(drop=0.03, bounce=0.02), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert "DROP_TOO_SMALL" not in s2.reason_codes


def test_debug_ultra_can_enter_sweep_on_small_drop():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    d.set_profile(DEBUG_ULTRA)
    s = d.detect(mt(drop=0.011, bounce=0.006, low=99.0), mt(drop=0.05), mt(drop=0.05), buf(ask=100.2))
    assert "SWEEP_FOUND" in s.reason_codes


def test_reclaim_before_hold_no_signal():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    b = buf(ask=100.2)
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    clock.advance(RECLAIM_HOLD_MS - 1)
    s = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert not s.detected


def test_slow_trend_blocks_signal():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    s = d.detect(mt(drop=0.2, bounce=0.05), mt(drop=0.1), mt(drop=1.0), buf())
    assert not s.detected
    assert "SLOW_TREND_TOO_DANGEROUS" in s.reason_codes


def test_new_low_after_reclaim_invalidates():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    b = buf(ask=100.2)
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    clock.advance(10)
    s = d.detect(mt(drop=0.2, bounce=0.05, low=98.5), mt(drop=0.1), mt(drop=0.1), b)
    assert "NEW_LOW_AFTER_RECLAIM" in s.reason_codes


def test_high_spread_resets_setup():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf())
    s = d.detect(mt(drop=0.2, bounce=0.05, spread=0.2), mt(drop=0.1), mt(drop=0.1), buf())
    assert not s.detected
    assert s.phase == "INVALIDATED"


def test_invalidation_cooldown_blocks_new_setup():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    d.detect(mt(drop=0.2, bounce=0.05, spread=0.2), mt(drop=0.1), mt(drop=0.1), buf())
    s = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf())
    assert not s.detected
    assert s.phase == "INVALIDATED"
    assert "INVALIDATION_COOLDOWN" in s.reason_codes
    clock.advance(INVALIDATION_COOLDOWN_MS + 1)
    s2 = d.detect(mt(drop=0.01), mt(), mt(), buf())
    assert s2.phase == "WATCHING_DROP"


def test_setup_too_old_invalidates():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=99.0))
    clock.advance(SETUP_MAX_AGE_MS + 1)
    s = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=99.0))
    assert "SETUP_TOO_OLD" in s.reason_codes


def test_reclaim_timeout_invalidates():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    clock.advance(1)
    d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=99.0))
    clock.advance(RECLAIM_TIMEOUT_MS + 1)
    s = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=99.0))
    assert "RECLAIM_TIMEOUT" in s.reason_codes

def test_would_signal_triggers_when_only_bounce_blocks():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    d.set_runtime_flags(signal_unlock_debug=True, p90_bounce_pct=0.02)
    s = d.detect(mt(drop=0.2, bounce=0.01, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert s.would_signal is True
    assert s.would_signal_reason == "WOULD_SIGNAL_BOUNCE"
    assert s.detected is False


def test_would_signal_triggers_when_only_hold_blocks():
    clock = FakeClock()
    d = LiquidityGrabDetector(now_ms_provider=clock)
    d.set_runtime_flags(signal_unlock_debug=True, p90_bounce_pct=0.05)
    b = buf(ask=100.2)
    s = d.detect(mt(drop=0.2, bounce=0.05, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert s.would_signal is True
    assert s.would_signal_reason == "WOULD_SIGNAL_HOLD"


def test_unlock_mode_does_not_modify_detected():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    d.set_runtime_flags(signal_unlock_debug=True, p90_bounce_pct=0.02)
    s = d.detect(mt(drop=0.2, bounce=0.01, low=99.0), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert s.detected is False


def test_unlock_mode_respects_spread_guard():
    d = LiquidityGrabDetector(now_ms_provider=FakeClock())
    d.set_runtime_flags(signal_unlock_debug=True, p90_bounce_pct=0.02)
    s = d.detect(mt(drop=0.2, bounce=0.01, low=99.0, spread=1.0), mt(drop=0.1), mt(drop=0.1), buf(ask=100.2))
    assert s.would_signal is False
