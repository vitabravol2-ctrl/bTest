import time

from app.config import (
    MAX_ALLOWED_SPREAD_PCT,
    MIN_GRAB_DROP_PCT,
    MIN_IMPULSE_SPEED_PCT_PER_SEC,
    MIN_RECLAIM_BOUNCE_PCT,
    MAX_TREND_DROP_MID_PCT,
    RECLAIM_HOLD_MS,
    SIGNAL_MIN_SCORE,
)
from app.market_buffer import MarketBuffer
from app.metrics import MarketMetrics
from app.signals import LiquidityGrabSignal


class LiquidityGrabDetector:
    def __init__(self) -> None:
        self._phase = "NO_SETUP"
        self._sweep_low: float | None = None
        self._reclaim_level: float | None = None
        self._reclaim_since_ms: int | None = None

    def detect(
        self,
        metrics_fast: MarketMetrics,
        metrics_mid: MarketMetrics,
        metrics_slow: MarketMetrics,
        buffer: MarketBuffer,
    ) -> LiquidityGrabSignal:
        _ = metrics_slow
        now_ms = int(time.time() * 1000)
        last = buffer.last()
        last_bid = last.bid if last else None
        reason_codes: list[str] = []

        if not (metrics_fast.enough_data and metrics_mid.enough_data):
            self._phase = "NO_SETUP"
            reason_codes.append("WAITING_DATA")
            return self._build(False, 0.0, reason_codes, "Waiting enough fast/mid data", now_ms, last_bid)

        if metrics_fast.stale or metrics_mid.stale:
            self._phase = "NO_SETUP"
            reason_codes.append("STALE_DATA")
            return self._build(False, 0.0, reason_codes, "Data is stale", now_ms, last_bid)

        if metrics_fast.spread_avg_pct > MAX_ALLOWED_SPREAD_PCT:
            self._phase = "NO_SETUP"
            reason_codes.append("HIGH_SPREAD")
            return self._build(False, 0.0, reason_codes, "Spread too high", now_ms, last_bid)

        if metrics_fast.drop_pct < MIN_GRAB_DROP_PCT:
            self._phase = "WATCHING_DROP"
            reason_codes.append("DROP_TOO_SMALL")
            return self._build(False, self._score(metrics_fast, metrics_mid), reason_codes, "Watching for stronger drop", now_ms, last_bid)

        self._phase = "LIQUIDITY_SWEEP"
        reason_codes.append("SWEEP_FOUND")
        self._sweep_low = metrics_fast.low
        self._reclaim_level = metrics_fast.last_mid

        if metrics_fast.bounce_pct < MIN_RECLAIM_BOUNCE_PCT:
            reason_codes.append("BOUNCE_TOO_SMALL")
            return self._build(False, self._score(metrics_fast, metrics_mid), reason_codes, "Sweep found, waiting reclaim bounce", now_ms, last_bid)

        speed_ok = abs(metrics_fast.impulse_speed_pct_per_sec) >= MIN_IMPULSE_SPEED_PCT_PER_SEC
        trend_ok = metrics_mid.drop_pct <= MAX_TREND_DROP_MID_PCT
        reclaim_ok = last_bid is not None and self._reclaim_level is not None and last_bid >= self._reclaim_level

        if not speed_ok:
            reason_codes.append("IMPULSE_TOO_SLOW")
        if not trend_ok:
            reason_codes.append("MID_TREND_TOO_DANGEROUS")
        if not reclaim_ok:
            reason_codes.append("BOUNCE_TOO_SMALL")

        if reclaim_ok:
            if self._reclaim_since_ms is None:
                self._reclaim_since_ms = now_ms
            hold_ok = (now_ms - self._reclaim_since_ms) >= RECLAIM_HOLD_MS
        else:
            self._reclaim_since_ms = None
            hold_ok = False

        no_new_low = self._sweep_low is None or metrics_fast.low >= self._sweep_low
        if reclaim_ok and hold_ok:
            self._phase = "RECLAIM_CONFIRMED"
            reason_codes.append("RECLAIM_CONFIRMED")

        score = self._score(metrics_fast, metrics_mid)
        hard_filters_ok = speed_ok and trend_ok and reclaim_ok and hold_ok and no_new_low
        if score >= SIGNAL_MIN_SCORE and hard_filters_ok:
            self._phase = "LONG_SIGNAL"
            reason_codes.append("LONG_SIGNAL_READY")
            return self._build(True, score, reason_codes, "Liquidity grab LONG signal ready", now_ms, last_bid)

        return self._build(False, score, reason_codes, "Reclaim in progress", now_ms, last_bid)

    def _score(self, metrics_fast: MarketMetrics, metrics_mid: MarketMetrics) -> float:
        drop_score = min(metrics_fast.drop_pct / MIN_GRAB_DROP_PCT, 1.0) * 25.0
        bounce_score = min(metrics_fast.bounce_pct / MIN_RECLAIM_BOUNCE_PCT, 1.0) * 25.0
        speed_score = min(abs(metrics_fast.impulse_speed_pct_per_sec) / MIN_IMPULSE_SPEED_PCT_PER_SEC, 1.0) * 20.0
        spread_ratio = max(0.0, 1.0 - (metrics_fast.spread_avg_pct / MAX_ALLOWED_SPREAD_PCT))
        spread_score = min(spread_ratio, 1.0) * 15.0
        trend_ratio = max(0.0, 1.0 - (metrics_mid.drop_pct / MAX_TREND_DROP_MID_PCT))
        trend_score = min(trend_ratio, 1.0) * 15.0
        return round(min(drop_score + bounce_score + speed_score + spread_score + trend_score, 100.0), 2)

    def _build(self, detected: bool, score: float, reason_codes: list[str], reason: str, now_ms: int, last_bid: float | None) -> LiquidityGrabSignal:
        return LiquidityGrabSignal(
            detected=detected,
            side="LONG" if detected else "NONE",
            score=score,
            phase=self._phase,
            trigger_price=last_bid,
            grab_low=self._sweep_low,
            reclaim_level=self._reclaim_level,
            reason_codes=reason_codes,
            human_reason=reason,
            ts_ms=now_ms,
        )
