import time
from typing import Callable

MIN_UNLOCK_BOUNCE_PCT = 0.003

from app.config import (
    FAST_WINDOW_MS,
    INVALIDATION_COOLDOWN_MS,
    MAX_ALLOWED_SPREAD_PCT,
    NEW_LOW_INVALIDATES_RECLAIM,
    RECLAIM_HOLD_MS,
    RECLAIM_TIMEOUT_MS,
    SETUP_MAX_AGE_MS,
    USE_SLOW_TREND_FILTER,
)
from app.market_buffer import MarketBuffer
from app.metrics import MarketMetrics
from app.profiles import BASELINE, ThresholdProfile
from app.signals import LiquidityGrabSignal


class LiquidityGrabDetector:
    def __init__(self, now_ms_provider: Callable[[], int] | None = None) -> None:
        self._now_ms = now_ms_provider or (lambda: int(time.time() * 1000))
        self._phase = "NO_SETUP"
        self._sweep_low: float | None = None
        self._reclaim_level: float | None = None
        self._reclaim_since_ms: int | None = None
        self._sweep_started_ms: int | None = None
        self._last_invalid_reason = "-"
        self._invalidated_until_ms: int = 0
        self.profile: ThresholdProfile = BASELINE
        self.signal_unlock_debug = False
        self.unlock_p90_bounce_pct = 0.0
        self.adaptive_hold_enabled = False

    def set_profile(self, profile: ThresholdProfile) -> None:
        self.profile = profile

    def set_runtime_flags(self, *, signal_unlock_debug: bool = False, p90_bounce_pct: float = 0.0, adaptive_hold_enabled: bool = True) -> None:
        self.signal_unlock_debug = bool(signal_unlock_debug)
        self.unlock_p90_bounce_pct = max(0.0, float(p90_bounce_pct))
        self.adaptive_hold_enabled = bool(adaptive_hold_enabled)

    def reset(self, reason: str) -> None:
        now_ms = self._now_ms()
        self._phase = "INVALIDATED"
        self._sweep_low = None
        self._reclaim_level = None
        self._reclaim_since_ms = None
        self._sweep_started_ms = None
        self._last_invalid_reason = reason
        self._invalidated_until_ms = now_ms + INVALIDATION_COOLDOWN_MS

    def detect(self, metrics_fast: MarketMetrics, metrics_mid: MarketMetrics, metrics_slow: MarketMetrics, buffer: MarketBuffer) -> LiquidityGrabSignal:
        now_ms = self._now_ms()
        last = buffer.last()
        price_for_reclaim = last.ask if last else None
        reason_codes: list[str] = []
        unlock_reason = ""
        unlock_blocker = ""
        debug = {
            "drop_ok": False,
            "bounce_ok": False,
            "speed_ok": False,
            "reclaim_ok": False,
            "hold_ok": False,
            "slow_trend_ok": True,
        }

        if now_ms < self._invalidated_until_ms:
            self._phase = "INVALIDATED"
            reason_codes.extend(["INVALIDATED", "INVALIDATION_COOLDOWN"])
            return self._build(False, 0.0, reason_codes, "Invalidation cooldown", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if self._phase == "INVALIDATED" and now_ms >= self._invalidated_until_ms:
            self._phase = "WATCHING_DROP"

        if not (metrics_fast.enough_data and metrics_mid.enough_data):
            self._phase = "NO_SETUP"
            reason_codes.append("WAITING_DATA")
            return self._build(False, 0.0, reason_codes, "Waiting enough fast/mid data", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if metrics_fast.stale or metrics_mid.stale:
            self.reset("STALE_DATA")
            reason_codes.extend(["STALE_DATA", "INVALIDATED"])
            return self._build(False, 0.0, reason_codes, "Data is stale", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if metrics_fast.spread_avg_pct > MAX_ALLOWED_SPREAD_PCT:
            self.reset("HIGH_SPREAD")
            reason_codes.extend(["HIGH_SPREAD", "INVALIDATED"])
            return self._build(False, 0.0, reason_codes, "Spread too high", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if USE_SLOW_TREND_FILTER and metrics_slow.drop_pct > self.profile.max_slow_trend_drop_pct:
            debug["slow_trend_ok"] = False
            self.reset("SLOW_TREND_TOO_DANGEROUS")
            reason_codes.extend(["SLOW_TREND_TOO_DANGEROUS", "INVALIDATED"])
            return self._build(False, 0.0, reason_codes, "Slow trend too dangerous", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if metrics_mid.drop_pct > self.profile.max_trend_drop_mid_pct:
            self.reset("MID_TREND_TOO_DANGEROUS")
            reason_codes.extend(["MID_TREND_TOO_DANGEROUS", "INVALIDATED"])
            return self._build(False, 0.0, reason_codes, "Mid trend too dangerous", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        if metrics_fast.drop_pct < self.profile.min_grab_drop_pct:
            self._phase = "WATCHING_DROP"
            reason_codes.append("DROP_TOO_SMALL")
            return self._build(False, self._score(metrics_fast, metrics_mid), reason_codes, "Watching for stronger drop", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        debug["drop_ok"] = True

        if self._phase in {"NO_SETUP", "WATCHING_DROP", "INVALIDATED"} or self._sweep_low is None:
            self._phase = "LIQUIDITY_SWEEP"
            self._sweep_low = metrics_fast.low
            self._sweep_started_ms = now_ms
            self._reclaim_since_ms = None
        elif metrics_fast.low < self._sweep_low:
            self._sweep_low = metrics_fast.low
            if self._reclaim_since_ms is not None and NEW_LOW_INVALIDATES_RECLAIM:
                self.reset("NEW_LOW_AFTER_RECLAIM")
                reason_codes.extend(["NEW_LOW_AFTER_RECLAIM", "INVALIDATED"])
                return self._build(False, self._score(metrics_fast, metrics_mid), reason_codes, "New low after reclaim", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)
            self._reclaim_since_ms = None

        reason_codes.append("SWEEP_FOUND")

        if self._sweep_started_ms is not None and (now_ms - self._sweep_started_ms) > SETUP_MAX_AGE_MS:
            self.reset("SETUP_TOO_OLD")
            reason_codes.extend(["SETUP_TOO_OLD", "INVALIDATED"])
            return self._build(False, 0.0, reason_codes, "Setup too old", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)

        drop_speed = metrics_fast.drop_pct / (FAST_WINDOW_MS / 1000)
        speed_ok = drop_speed >= self.profile.min_impulse_speed_pct_per_sec
        base_bounce_threshold = self.profile.min_reclaim_bounce_pct
        effective_bounce_threshold = base_bounce_threshold
        reclaim_level_source = "EFFECTIVE_BOUNCE"
        if self.signal_unlock_debug:
            if self.unlock_p90_bounce_pct > 0:
                effective_bounce_threshold = max(MIN_UNLOCK_BOUNCE_PCT, min(base_bounce_threshold, self.unlock_p90_bounce_pct * 0.75))
                reclaim_level_source = "adaptive_unlock_p90_0.75"
            else:
                reclaim_level_source = "base_bounce_threshold_unlock_p90_zero"
        self._reclaim_level = self._sweep_low * (1 + (effective_bounce_threshold / 100.0)) if self._sweep_low is not None else None
        actual_bounce_pct = metrics_fast.bounce_pct
        bounce_ok = actual_bounce_pct >= effective_bounce_threshold
        bounce_gap_pct = effective_bounce_threshold - actual_bounce_pct
        reclaim_ok = price_for_reclaim is not None and self._reclaim_level is not None and price_for_reclaim >= self._reclaim_level
        reclaim_distance_pct = 0.0
        if price_for_reclaim is not None and self._reclaim_level is not None and self._reclaim_level != 0:
            reclaim_distance_pct = ((price_for_reclaim - self._reclaim_level) / self._reclaim_level) * 100.0

        debug["speed_ok"] = speed_ok
        debug["bounce_ok"] = bounce_ok
        debug["reclaim_ok"] = reclaim_ok
        score = self._score(metrics_fast, metrics_mid, bounce_threshold_for_score=(effective_bounce_threshold if self.signal_unlock_debug else None))
        adaptive_hold_active = bool(self.adaptive_hold_enabled)
        base_hold_ms = RECLAIM_HOLD_MS
        effective_hold_ms = RECLAIM_HOLD_MS
        hold_reason = "base"

        if not speed_ok:
            reason_codes.append("IMPULSE_TOO_SLOW")

        if not bounce_ok:
            reason_codes.append("BOUNCE_TOO_SMALL")
            self._phase = "LIQUIDITY_SWEEP" if self._reclaim_since_ms is None else "RECLAIM_WAIT"
            would_signal = False
            would_signal_reason = ""
            if self.signal_unlock_debug and score >= max(70.0, self.profile.signal_min_score) and not metrics_fast.stale and metrics_fast.spread_avg_pct <= MAX_ALLOWED_SPREAD_PCT and bool(debug.get("slow_trend_ok", True)) and "SWEEP_FOUND" in reason_codes and speed_ok:
                would_signal = True
                unlock_blocker = "bounce_ok"
                would_signal_reason = "WOULD_SIGNAL_BOUNCE"
                unlock_reason = would_signal_reason
            return self._build(False, score, reason_codes, "Bounce too small", now_ms, price_for_reclaim, debug, would_signal=would_signal, would_signal_reason=would_signal_reason, unlock_debug_active=self.signal_unlock_debug, unlock_blocker=unlock_blocker, unlock_reason=unlock_reason, adaptive_hold_active=adaptive_hold_active, base_hold_ms=base_hold_ms, effective_hold_ms=effective_hold_ms, hold_reduction_reason=hold_reason, effective_bounce_threshold=effective_bounce_threshold, base_bounce_threshold=base_bounce_threshold, reclaim_level_source=reclaim_level_source, reclaim_distance_pct=reclaim_distance_pct, actual_bounce_pct=actual_bounce_pct, bounce_gap_pct=bounce_gap_pct, bounce_ok_effective=bounce_ok)

        if reclaim_ok:
            self._phase = "RECLAIM_WAIT"
            reason_codes.append("RECLAIM_WAIT")
            if self._reclaim_since_ms is None:
                self._reclaim_since_ms = now_ms
            hold_ms = now_ms - self._reclaim_since_ms
            required_hold_ms = RECLAIM_HOLD_MS
            hold_reason = "base"
            if self.adaptive_hold_enabled:
                if score >= 90:
                    required_hold_ms = int(RECLAIM_HOLD_MS * 0.35)
                    hold_reason = "score>=90"
                elif score >= 80:
                    required_hold_ms = int(RECLAIM_HOLD_MS * 0.50)
                    hold_reason = "score>=80"
                elif score >= 70:
                    required_hold_ms = int(RECLAIM_HOLD_MS * 0.70)
                    hold_reason = "score>=70"
                if bounce_ok and speed_ok and reclaim_ok:
                    required_hold_ms = int(required_hold_ms * 0.80)
                    hold_reason = f"{hold_reason}+quality"
                required_hold_ms = max(80, min(RECLAIM_HOLD_MS, required_hold_ms))
            effective_hold_ms = required_hold_ms
            if hold_ms >= required_hold_ms:
                reason_codes.append("RECLAIM_CONFIRMED")
                reason_codes.append("RECLAIM_HOLDING")
                self._phase = "RECLAIM_CONFIRMED"
            else:
                reason_codes.append("RECLAIM_HOLDING")
        else:
            if self._sweep_started_ms is not None and (now_ms - self._sweep_started_ms) > RECLAIM_TIMEOUT_MS:
                self.reset("RECLAIM_TIMEOUT")
                reason_codes.extend(["RECLAIM_TIMEOUT", "INVALIDATED"])
                return self._build(False, self._score(metrics_fast, metrics_mid), reason_codes, "Reclaim timeout", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug)
            self._reclaim_since_ms = None
            reason_codes.append("RECLAIM_WAIT")

        hold_ok = self._phase == "RECLAIM_CONFIRMED"
        debug["hold_ok"] = hold_ok
        if score >= self.profile.signal_min_score and speed_ok and reclaim_ok and hold_ok:
            self._phase = "LONG_SIGNAL"
            reason_codes.append("LONG_SIGNAL_READY")
            return self._build(True, score, reason_codes, "Liquidity grab LONG signal ready", now_ms, price_for_reclaim, debug, unlock_debug_active=self.signal_unlock_debug, effective_bounce_threshold=effective_bounce_threshold, base_bounce_threshold=base_bounce_threshold, reclaim_level_source=reclaim_level_source, reclaim_distance_pct=reclaim_distance_pct, actual_bounce_pct=actual_bounce_pct, bounce_gap_pct=bounce_gap_pct, bounce_ok_effective=bounce_ok)

        would_signal = False
        would_signal_reason = ""
        if self.signal_unlock_debug and score >= max(70.0, self.profile.signal_min_score) and not metrics_fast.stale and metrics_fast.spread_avg_pct <= MAX_ALLOWED_SPREAD_PCT and bool(debug.get("slow_trend_ok", True)):
            fails = [k for k in ("drop_ok", "bounce_ok", "speed_ok", "reclaim_ok", "hold_ok", "slow_trend_ok") if not bool(debug.get(k, False))]
            if len(fails) == 1 and fails[0] in {"bounce_ok", "hold_ok"} and "SWEEP_FOUND" in reason_codes and "RECLAIM_WAIT" in reason_codes and speed_ok:
                would_signal = True
                unlock_blocker = fails[0]
                would_signal_reason = "WOULD_SIGNAL_BOUNCE" if fails[0] == "bounce_ok" else "WOULD_SIGNAL_HOLD"
                unlock_reason = would_signal_reason

        return self._build(False, score, reason_codes, "Reclaim in progress", now_ms, price_for_reclaim, debug, would_signal=would_signal, would_signal_reason=would_signal_reason, unlock_debug_active=self.signal_unlock_debug, unlock_blocker=unlock_blocker, unlock_reason=unlock_reason, adaptive_hold_active=adaptive_hold_active, base_hold_ms=base_hold_ms, effective_hold_ms=effective_hold_ms, hold_reduction_reason=hold_reason, effective_bounce_threshold=effective_bounce_threshold, base_bounce_threshold=base_bounce_threshold, reclaim_level_source=reclaim_level_source, reclaim_distance_pct=reclaim_distance_pct, actual_bounce_pct=actual_bounce_pct, bounce_gap_pct=bounce_gap_pct, bounce_ok_effective=bounce_ok)

    def _score(self, metrics_fast: MarketMetrics, metrics_mid: MarketMetrics, bounce_threshold_for_score: float | None = None) -> float:
        drop_score = min(metrics_fast.drop_pct / self.profile.min_grab_drop_pct, 1.0) * 25.0
        bounce_threshold = bounce_threshold_for_score if bounce_threshold_for_score and bounce_threshold_for_score > 0 else self.profile.min_reclaim_bounce_pct
        bounce_score = min(metrics_fast.bounce_pct / bounce_threshold, 1.0) * 25.0
        drop_speed = metrics_fast.drop_pct / (FAST_WINDOW_MS / 1000)
        speed_score = min(drop_speed / self.profile.min_impulse_speed_pct_per_sec, 1.0) * 20.0
        spread_ratio = max(0.0, 1.0 - (metrics_fast.spread_avg_pct / MAX_ALLOWED_SPREAD_PCT))
        spread_score = min(spread_ratio, 1.0) * 15.0
        trend_ratio = max(0.0, 1.0 - (metrics_mid.drop_pct / self.profile.max_trend_drop_mid_pct))
        trend_score = min(trend_ratio, 1.0) * 15.0
        return round(min(drop_score + bounce_score + speed_score + spread_score + trend_score, 100.0), 2)

    def _build(self, detected: bool, score: float, reason_codes: list[str], reason: str, now_ms: int, trigger_price: float | None, debug: dict[str, bool], *, would_signal: bool = False, would_signal_reason: str = "", unlock_debug_active: bool = False, unlock_blocker: str = "", unlock_reason: str = "", adaptive_hold_active: bool = False, base_hold_ms: int = RECLAIM_HOLD_MS, effective_hold_ms: int = RECLAIM_HOLD_MS, hold_reduction_reason: str = "base", effective_bounce_threshold: float = 0.0, base_bounce_threshold: float = 0.0, reclaim_level_source: str = "base_bounce_threshold", reclaim_distance_pct: float = 0.0, actual_bounce_pct: float = 0.0, bounce_gap_pct: float = 0.0, bounce_ok_effective: bool = False) -> LiquidityGrabSignal:
        reclaim_hold_ms = (now_ms - self._reclaim_since_ms) if self._reclaim_since_ms is not None else 0
        setup_age_ms = (now_ms - self._sweep_started_ms) if self._sweep_started_ms is not None else 0
        return LiquidityGrabSignal(
            detected=detected,
            side="LONG" if detected else "NONE",
            score=score,
            phase=self._phase,
            trigger_price=trigger_price,
            grab_low=self._sweep_low,
            reclaim_level=self._reclaim_level,
            reason_codes=reason_codes,
            human_reason=reason,
            ts_ms=now_ms,
            setup_age_ms=setup_age_ms,
            reclaim_hold_ms=reclaim_hold_ms,
            last_invalid_reason=self._last_invalid_reason,
            debug=debug,
            would_signal=would_signal,
            would_signal_reason=would_signal_reason,
            unlock_debug_active=unlock_debug_active,
            unlock_blocker=unlock_blocker,
            unlock_reason=unlock_reason,
            adaptive_hold_active=adaptive_hold_active,
            base_hold_ms=base_hold_ms,
            effective_hold_ms=effective_hold_ms,
            hold_reduction_reason=hold_reduction_reason,
            effective_bounce_threshold=effective_bounce_threshold,
            base_bounce_threshold=base_bounce_threshold,
            reclaim_level_source=reclaim_level_source,
            reclaim_distance_pct=reclaim_distance_pct,
            actual_bounce_pct=actual_bounce_pct,
            bounce_gap_pct=bounce_gap_pct,
            bounce_ok_effective=bounce_ok_effective,
        )
