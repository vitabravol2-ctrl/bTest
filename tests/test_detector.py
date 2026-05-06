from app.detector import LiquidityGrabDetector
from app.market_buffer import MarketBuffer
from app.metrics import MarketMetrics
from app.models import MarketTick


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
    d = LiquidityGrabDetector()
    s = d.detect(mt(enough=False), mt(), mt(), buf())
    assert not s.detected
    assert "WAITING_DATA" in s.reason_codes


def test_drop_too_small_no_signal():
    d = LiquidityGrabDetector()
    s = d.detect(mt(drop=0.01), mt(), mt(), buf())
    assert not s.detected
    assert s.phase == "WATCHING_DROP"


def test_sweep_then_reclaim_long_signal():
    d = LiquidityGrabDetector()
    b = buf(bid=100.0, ask=100.2)
    s1 = d.detect(mt(drop=0.2, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert not s1.detected
    d._reclaim_since_ms = 0
    s2 = d.detect(mt(drop=0.2, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    assert s2.reclaim_level is not None


def test_slow_trend_blocks_signal():
    d = LiquidityGrabDetector()
    s = d.detect(mt(drop=0.2), mt(drop=0.1), mt(drop=1.0), buf())
    assert not s.detected
    assert "SLOW_TREND_TOO_DANGEROUS" in s.reason_codes


def test_new_low_after_reclaim_invalidates():
    d = LiquidityGrabDetector()
    b = buf()
    d.detect(mt(drop=0.2, low=99.0), mt(drop=0.1), mt(drop=0.1), b)
    d._reclaim_since_ms = 1
    s = d.detect(mt(drop=0.2, low=98.5), mt(drop=0.1), mt(drop=0.1), b)
    assert "NEW_LOW_AFTER_RECLAIM" in s.reason_codes


def test_high_spread_resets_setup():
    d = LiquidityGrabDetector()
    d.detect(mt(drop=0.2, low=99.0), mt(drop=0.1), mt(drop=0.1), buf())
    s = d.detect(mt(drop=0.2, spread=0.2), mt(drop=0.1), mt(drop=0.1), buf())
    assert not s.detected
    assert s.phase == "INVALIDATED"
