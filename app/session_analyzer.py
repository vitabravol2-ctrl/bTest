from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any


class SessionAnalyzer:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.events: list[dict[str, Any]] = []
        self.report_text: str = ""
        self.report_data: dict[str, Any] = {}

    def load(self, path: str | Path) -> int:
        self.path = Path(path)
        self.events = []
        if not self.path.exists():
            raise FileNotFoundError(f"Session file not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.events.append(json.loads(line))
        return len(self.events)

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(pct * (len(sorted_vals) - 1))
        return float(sorted_vals[idx])

    @classmethod
    def _p95(cls, values: list[float]) -> float:
        return cls._percentile(values, 0.95)

    @classmethod
    def _p75(cls, values: list[float]) -> float:
        return cls._percentile(values, 0.75)

    @classmethod
    def _p90(cls, values: list[float]) -> float:
        return cls._percentile(values, 0.90)

    def suggest_profile(self) -> dict[str, Any]:
        if not self.report_data:
            self.analyze()
        hints = self.report_data.get("threshold_hints", {})
        near_signals_count = int(self.report_data.get("near_signals_count", 0))

        p90_drop_pct = float(hints.get("p90_drop_pct", 0.0))
        p95_drop_pct = float(hints.get("p95_drop_pct", 0.0))
        p90_bounce_pct = float(hints.get("p90_bounce_pct", 0.0))
        p95_bounce_pct = float(hints.get("p95_bounce_pct", 0.0))
        near_signal_bounce_median = float(hints.get("near_signal_bounce_median", 0.0))
        p75_abs_speed = float(hints.get("p75_abs_speed", 0.0))
        reclaim_hints = self.report_data.get("reclaim_hints", {})

        drop_value = max(0.005, p90_drop_pct * 0.70)
        if p95_drop_pct > 0:
            drop_value = min(drop_value, p95_drop_pct * 0.70)

        if near_signals_count > 0:
            near_median_component = near_signal_bounce_median * 0.80 if near_signal_bounce_median > 0 else p90_bounce_pct * 0.80
            min_reclaim_bounce_pct = max(0.005, min(p90_bounce_pct * 0.80, near_median_component))
        else:
            min_reclaim_bounce_pct = max(0.005, p90_bounce_pct * 0.80)
        if p95_bounce_pct > 0:
            min_reclaim_bounce_pct = min(min_reclaim_bounce_pct, p95_bounce_pct * 0.55)

        suggested = {
            "name": "CALIBRATED",
            "min_grab_drop_pct": drop_value,
            "min_reclaim_bounce_pct": min_reclaim_bounce_pct,
            "min_impulse_speed_pct_per_sec": max(0.0005, p75_abs_speed * 0.60),
            "signal_min_score": 55 if near_signals_count > 0 else 60,
            "max_trend_drop_mid_pct": 0.25,
            "max_slow_trend_drop_pct": 0.40,
            "reason": [
                "drop threshold uses p90*0.70",
                "bounce threshold uses p90*0.80 and near-signal median",
                "upper clamp prevents overblocking",
                "speed uses p75 abs speed",
                f"p90_drop_pct={p90_drop_pct:.5f}",
                f"p95_drop_pct={p95_drop_pct:.5f}",
                f"p90_bounce_pct={p90_bounce_pct:.5f}",
                f"p95_bounce_pct={p95_bounce_pct:.5f}",
                f"near_signal_bounce_median={near_signal_bounce_median:.5f}",
                f"p75_abs_speed={p75_abs_speed:.5f}",
                f"near_signals_count={near_signals_count}",
                f"near_signal_blockers={self.report_data.get('near_signal_blockers', {})}",
                f"pass_drop_ok={hints.get('pass_drop_ok', 0)} pass_drop_bounce={hints.get('pass_drop_bounce', 0)}",
                f"pass_drop_bounce_reclaim={hints.get('pass_drop_bounce_reclaim', 0)} pass_hold_ok={hints.get('pass_hold_ok', 0)}",
                f"max_drop_pct={hints.get('max_drop_pct', 0.0):.5f}",
            ],
            "runtime_params": {
                "min_reclaim_hold_ms": int(reclaim_hints.get("suggested_min_reclaim_hold_ms", 150)),
                "reclaim_window_ms": int(reclaim_hints.get("suggested_reclaim_window_ms", 3000)),
                "invalidation_cooldown_ms": int(reclaim_hints.get("suggested_invalidation_cooldown_ms", 1000)),
            },
        }
        if int(self.report_data.get("would_signal_count", 0)) > 0 and int(self.report_data.get("detected_count", 0)) == 0:
            suggested["reason"].append("unlock debug indicates softer bounce/hold may unlock real signals")
        return suggested

    def analyze(self, current_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        scores = [float(e.get("score", 0.0)) for e in self.events]
        detected_count = sum(1 for e in self.events if bool(e.get("detected", False)))
        would_signals = [e for e in self.events if bool(e.get("would_signal", False))]

        profile_counts = Counter(str(e.get("profile_name", "UNKNOWN")) for e in self.events)
        phase_counts = Counter(str(e.get("phase", "UNKNOWN")) for e in self.events)

        reason_code_counts: Counter[str] = Counter()
        for e in self.events:
            reason_code_counts.update(str(code) for code in e.get("reason_codes", []))

        fail_counts = Counter({k: 0 for k in ("drop_ok", "bounce_ok", "speed_ok", "reclaim_ok", "hold_ok", "slow_trend_ok")})
        for e in self.events:
            debug = e.get("debug", {}) or {}
            for key in fail_counts:
                if not bool(debug.get(key, False)):
                    fail_counts[key] += 1

        near_signals = [e for e in self.events if float(e.get("score", 0.0)) >= 50.0 and not bool(e.get("detected", False))]
        near_blockers: Counter[str] = Counter()
        top_near_events: list[dict[str, Any]] = []
        for e in near_signals:
            debug = e.get("debug", {}) or {}
            blocker = "unknown"
            for key in ("drop_ok", "bounce_ok", "speed_ok", "reclaim_ok", "hold_ok", "slow_trend_ok"):
                if not bool(debug.get(key, False)):
                    blocker = key
                    break
            near_blockers[blocker] += 1
            top_near_events.append(
                {
                    "ts": e.get("ts"),
                    "score": float(e.get("score", 0.0)),
                    "phase": e.get("phase", "UNKNOWN"),
                    "blocker": blocker,
                    "profile": e.get("profile_name", "UNKNOWN"),
                    "drop_pct": float(e.get("drop_pct", 0.0)),
                    "bounce_pct": float(e.get("bounce_pct", 0.0)),
                    "speed": float(e.get("speed", 0.0)),
                }
            )

        top_near_events = sorted(top_near_events, key=lambda x: x["score"], reverse=True)[:20]

        drop_values = [float(e.get("drop_pct", 0.0)) for e in self.events]
        bounce_values = [float(e.get("bounce_pct", 0.0)) for e in self.events]
        speed_values = [float(e.get("speed", 0.0)) for e in self.events]
        near_signal_bounce_values = [float(e.get("bounce_pct", 0.0)) for e in near_signals]
        drop_speed_abs_values = [abs(float(e.get("speed", 0.0))) for e in self.events if float(e.get("drop_pct", 0.0)) > 0]

        pass_drop = 0
        pass_drop_bounce = 0
        pass_drop_bounce_reclaim = 0
        pass_hold = 0
        sweep_events = [e for e in self.events if str(e.get("phase", "")) == "LIQUIDITY_SWEEP"]
        reclaim_wait_events = [e for e in self.events if str(e.get("phase", "")) == "RECLAIM_WAIT"]
        invalidated_after_sweep = [e for e in self.events if str(e.get("phase", "")) == "INVALIDATED"]
        detected_after_sweep = [e for e in self.events if bool(e.get("detected", False)) and str(e.get("phase", "")) in {"RECLAIM_WAIT", "SIGNAL_READY", "SIGNALLED"}]
        setup_age_values = [float(e.get("setup_age_ms", 0.0)) for e in self.events if float(e.get("setup_age_ms", 0.0)) > 0]
        reclaim_hold_values = [float(e.get("reclaim_hold_ms", 0.0)) for e in self.events if float(e.get("reclaim_hold_ms", 0.0)) > 0]
        post_sweep = [e for e in self.events if str(e.get("phase", "")) in {"RECLAIM_WAIT", "INVALIDATED", "BACK_TO_WATCHING", "SIGNAL_READY", "SIGNALLED"}]
        post_sweep_blockers: Counter[str] = Counter()
        for e in post_sweep:
            debug = e.get("debug", {}) or {}
            for key in ("drop_ok", "bounce_ok", "speed_ok", "reclaim_ok", "hold_ok", "slow_trend_ok"):
                if not bool(debug.get(key, False)):
                    post_sweep_blockers[key] += 1
                    break
        for e in self.events:
            debug = e.get("debug", {}) or {}
            if bool(debug.get("drop_ok", False)):
                pass_drop += 1
                if bool(debug.get("bounce_ok", False)):
                    pass_drop_bounce += 1
                    if bool(debug.get("reclaim_ok", False)):
                        pass_drop_bounce_reclaim += 1
            if bool(debug.get("hold_ok", False)):
                pass_hold += 1

        effective_hold_values = [float(e.get("effective_hold_ms", 0.0)) for e in self.events if float(e.get("effective_hold_ms", 0.0)) > 0]
        adaptive_active_count = sum(1 for e in self.events if bool(e.get("adaptive_hold_active", False)))
        hold_blocker_count = int(fail_counts.get("hold_ok", 0))
        detected_after_adaptive_hold = sum(1 for e in self.events if bool(e.get("detected", False)) and bool(e.get("adaptive_hold_active", False)) and float(e.get("effective_hold_ms", 0.0)) < float(e.get("base_hold_ms", 0.0)))

        would_signal_reasons = Counter(str(e.get("would_signal_reason", "UNKNOWN")) for e in would_signals if e.get("would_signal_reason"))
        would_after_sweep = sum(1 for e in would_signals if "SWEEP_FOUND" in (e.get("reason_codes") or []))
        effective_bounce_values = [float(e.get("effective_bounce_threshold", 0.0)) for e in self.events if float(e.get("effective_bounce_threshold", 0.0)) > 0.0]
        reclaim_distance_values = [float(e.get("reclaim_distance_pct", 0.0)) for e in self.events]
        would_signal_bounce_count = sum(1 for e in would_signals if str(e.get("would_signal_reason", "")) == "WOULD_SIGNAL_BOUNCE")
        would_signal_hold_count = sum(1 for e in would_signals if str(e.get("would_signal_reason", "")) == "WOULD_SIGNAL_HOLD")
        raw_signals = sum(1 for e in self.events if str(e.get("signal", "")) == "LONG_SIGNAL" or bool(e.get("detected", False)))
        grouped_signals = len({int(e.get("signal_group_id", 0)) for e in self.events if int(e.get("signal_group_id", 0)) > 0})
        grade_counts = Counter(str(e.get("signal_quality_grade", e.get("signal_grade", ""))) for e in self.events if str(e.get("signal_quality_grade", e.get("signal_grade", ""))) in {"A_PLUS", "A", "B", "C", "TRASH"})
        closed_trades = [e for e in self.events if str(e.get("paper_trade_result", "")) in {"WIN", "LOSS", "TIMEOUT"}]
        pnls = [float(e.get("paper_trade_pnl_pct", 0.0)) for e in closed_trades]
        wins = sum(1 for e in closed_trades if e.get("paper_trade_result") == "WIN")
        losses = sum(1 for e in closed_trades if e.get("paper_trade_result") == "LOSS")
        timeouts = sum(1 for e in closed_trades if e.get("paper_trade_result") == "TIMEOUT")
        total_events = len(self.events)
        data = {
            "total_events": total_events,
            "detected_count": detected_count,
            "max_score": max(scores) if scores else 0.0,
            "would_signal_count": len(would_signals),
            "would_signal_after_sweep": would_after_sweep,
            "would_signal_reasons": dict(would_signal_reasons),
            "would_signal_rate": (len(would_signals) / len(self.events) * 100.0) if self.events else 0.0,
            "avg_score": mean(scores) if scores else 0.0,
            "profile_counts": dict(profile_counts),
            "phase_counts": dict(phase_counts),
            "reason_code_counts": dict(reason_code_counts),
            "fail_counts": dict(fail_counts),
            "near_signals_count": len(near_signals),
            "near_signal_blockers": dict(near_blockers),
            "near_signal_top20": top_near_events,
            "threshold_hints": {
                "max_drop_pct": max(drop_values) if drop_values else 0.0,
                "p90_drop_pct": self._p90(drop_values),
                "p95_drop_pct": self._p95(drop_values),
                "max_bounce_pct": max(bounce_values) if bounce_values else 0.0,
                "p90_bounce_pct": self._p90(bounce_values),
                "p95_bounce_pct": self._p95(bounce_values),
                "max_speed": max(speed_values) if speed_values else 0.0,
                "p95_speed": self._p95(speed_values),
                "near_signal_bounce_p75": self._p75(near_signal_bounce_values) if near_signal_bounce_values else 0.0,
                "near_signal_bounce_median": float(median(near_signal_bounce_values)) if near_signal_bounce_values else 0.0,
                "p75_abs_speed": self._p75(drop_speed_abs_values) if drop_speed_abs_values else 0.0,
                "pass_drop_ok": pass_drop,
                "pass_drop_bounce": pass_drop_bounce,
                "pass_drop_bounce_reclaim": pass_drop_bounce_reclaim,
                "pass_hold_ok": pass_hold,
            },
            "post_sweep_analysis": {
                "total_sweeps": len(sweep_events),
                "reclaim_wait_count": len(reclaim_wait_events),
                "invalidated_after_sweep_count": len(invalidated_after_sweep),
                "detected_after_sweep_count": len(detected_after_sweep),
                "reclaim_success_rate": (len(reclaim_wait_events) / len(sweep_events) * 100.0) if sweep_events else 0.0,
                "signal_success_rate": (len(detected_after_sweep) / len(sweep_events) * 100.0) if sweep_events else 0.0,
                "avg_setup_age_ms": mean(setup_age_values) if setup_age_values else 0.0,
                "median_setup_age_ms": float(median(setup_age_values)) if setup_age_values else 0.0,
                "p75_setup_age_ms": self._p75(setup_age_values) if setup_age_values else 0.0,
                "median_reclaim_hold_ms": float(median(reclaim_hold_values)) if reclaim_hold_values else 0.0,
                "p75_reclaim_hold_ms": self._p75(reclaim_hold_values) if reclaim_hold_values else 0.0,
                "max_reclaim_hold_ms": max(reclaim_hold_values) if reclaim_hold_values else 0.0,
                "top_invalidation_reasons": dict(Counter(str(e.get("last_invalid_reason", "UNKNOWN")) for e in invalidated_after_sweep).most_common(5)),
                "top_blockers_after_sweep": dict(post_sweep_blockers.most_common(5)),
                "top_post_sweep_events": sorted(
                    [{"ts": e.get("ts"), "score": float(e.get("score", 0.0)), "phase": e.get("phase", "UNKNOWN")} for e in post_sweep],
                    key=lambda x: x["score"],
                    reverse=True,
                )[:20],
            },
        }
        p75_hold = data["post_sweep_analysis"]["p75_reclaim_hold_ms"]
        p75_setup = data["post_sweep_analysis"]["p75_setup_age_ms"]
        top_unlock_blockers = dict(Counter(str(e.get("unlock_blocker", "")) for e in would_signals if e.get("unlock_blocker")).most_common(5))
        avg_would_score = mean([float(e.get("score", 0.0)) for e in would_signals]) if would_signals else 0.0
        recommendation = "STILL_NO_SIGNAL"
        if len(would_signals) > 0 and detected_count == 0:
            reasons = dict(would_signal_reasons)
            if reasons.get("WOULD_SIGNAL_HOLD", 0) >= reasons.get("WOULD_SIGNAL_BOUNCE", 0):
                recommendation = "HOLD_TOO_STRICT"
            else:
                recommendation = "BOUNCE_TOO_STRICT"
        elif detected_count > 0:
            recommendation = "SIGNAL_READY"
        data["signal_unlock_analysis"] = {
            "would_signals": len(would_signals),
            "would_signals_after_sweep": would_after_sweep,
            "top_unlock_blockers": top_unlock_blockers,
            "avg_would_signal_score": avg_would_score,
            "reclaim_success_before_would_signal": data["post_sweep_analysis"]["reclaim_success_rate"],
            "recommendation": recommendation,
        }
        bounce_blocker_count = int(fail_counts.get("bounce_ok", 0))
        reclaim_blocker_count = int(fail_counts.get("reclaim_ok", 0))
        bounce_recommendation = "READY_FOR_SIGNAL_QUALITY"
        if bounce_blocker_count > reclaim_blocker_count and bounce_blocker_count > 0:
            bounce_recommendation = "BOUNCE_TOO_STRICT"
        elif reclaim_blocker_count > bounce_blocker_count and reclaim_blocker_count > 0:
            bounce_recommendation = "RECLAIM_LEVEL_TOO_STRICT"
        elif bounce_blocker_count == 0 and reclaim_blocker_count == 0:
            bounce_recommendation = "BOUNCE_OK"
        data["bounce_reclaim_alignment_analysis"] = {
            "base_bounce_threshold": float((self.events[0] if self.events else {}).get("thresholds", {}).get("min_reclaim_bounce_pct", 0.0)),
            "effective_bounce_threshold_median": float(median(effective_bounce_values)) if effective_bounce_values else 0.0,
            "effective_bounce_threshold_p75": self._p75(effective_bounce_values) if effective_bounce_values else 0.0,
            "reclaim_distance_median_pct": float(median(reclaim_distance_values)) if reclaim_distance_values else 0.0,
            "reclaim_distance_p75_pct": self._p75(reclaim_distance_values) if reclaim_distance_values else 0.0,
            "bounce_blocker_count": bounce_blocker_count,
            "reclaim_blocker_count": reclaim_blocker_count,
            "would_signal_bounce_count": would_signal_bounce_count,
            "would_signal_hold_count": would_signal_hold_count,
            "detected_count": detected_count,
            "recommendation": bounce_recommendation,
        }


        adaptive_recommendation = "NEED_MORE_DATA"
        detected_rate = (detected_count / total_events) if total_events else 0.0
        if detected_rate > 0.05 or (len(would_signals) > 0 and detected_count > len(would_signals) * 0.75):
            adaptive_recommendation = "HOLD_TOO_SOFT"
        elif total_events < 100:
            adaptive_recommendation = "NEED_MORE_DATA"
        elif detected_count > 0:
            adaptive_recommendation = "HOLD_OK"
        elif hold_blocker_count > 0 and len(would_signals) > 0:
            adaptive_recommendation = "HOLD_STILL_TOO_STRICT"

        data["adaptive_hold_analysis"] = {
            "detected_count": detected_count,
            "would_signal_count": len(would_signals),
            "hold_blocker_count": hold_blocker_count,
            "effective_hold_median": float(median(effective_hold_values)) if effective_hold_values else 0.0,
            "effective_hold_p75": self._p75(effective_hold_values) if effective_hold_values else 0.0,
            "adaptive_hold_active_count": adaptive_active_count,
            "detected_after_adaptive_hold": detected_after_adaptive_hold,
            "recommendation": adaptive_recommendation,
        }

        data["signal_quality_paper"] = {
            "raw_signals": raw_signals,
            "grouped_signals": grouped_signals,
            "market_events": grouped_signals,
            "duplicate_signals_suppressed": sum(1 for e in self.events if bool(e.get("is_duplicate_signal", False))),
            "average_quality_score": (mean([float(e.get("signal_quality_score", 0.0)) for e in self.events if float(e.get("signal_quality_score", 0.0)) > 0]) if [float(e.get("signal_quality_score", 0.0)) for e in self.events if float(e.get("signal_quality_score", 0.0)) > 0] else 0.0),
            "top_trash_reasons": dict(Counter(r for e in self.events for r in (e.get("signal_quality_reasons", []) or []) if str(e.get("signal_quality_grade", "")) == "TRASH").most_common(5)),
            "top_downgrade_reasons": dict(Counter(r for e in self.events for r in (e.get("signal_quality_reasons", []) or [])).most_common(5)),
            "grade_counts": dict(grade_counts),
            "paper_trades": len(closed_trades),
            "wins": wins,
            "losses": losses,
            "timeouts": timeouts,
            "winrate": (wins / len(closed_trades) * 100.0) if closed_trades else 0.0,
            "avg_pnl": (sum(pnls) / len(pnls)) if pnls else 0.0,
            "total_pnl": sum(pnls) if pnls else 0.0,
            "max_favorable_avg": 0.0,
            "max_adverse_avg": 0.0,
            "post_signal_performance": {},
            "recommendation": "NEED_MORE_DATA",
        }
        if raw_signals > 0 and grouped_signals and raw_signals / max(1, grouped_signals) > 3:
            data["signal_quality_paper"]["recommendation"] = "SPAM_SIGNALS_GROUPING_NEEDED"
        elif len(closed_trades) >= 5:
            wr = data["signal_quality_paper"]["winrate"]
            data["signal_quality_paper"]["recommendation"] = "SIGNALS_GOOD_ENOUGH_FOR_MORE_TESTING" if wr >= 50 else "TOO_MANY_FALSE_SIGNALS"

        data["reclaim_hints"] = {
            "suggested_min_reclaim_hold_ms": int(max(100, min(800, p75_hold * 0.70))) if p75_hold > 0 else 150,
            "suggested_reclaim_window_ms": int(max(1000, min(8000, p75_setup * 1.50))) if p75_setup > 0 else 3000,
            "suggested_invalidation_cooldown_ms": 1000,
        }
        self.report_data = data
        suggested = self.suggest_profile()
        data["suggested_profile"] = suggested
        data["calibration_validation"] = self.validate_calibration_before_after(
            current_profile=current_profile or {},
            suggested_profile=suggested,
        )
        self.report_data = data
        self.report_text = self._format_report(data)
        return data

    def validate_calibration_before_after(
        self,
        current_profile: dict[str, Any],
        suggested_profile: dict[str, Any],
        *,
        min_research_ticks: int = 300,
        min_sweeps_for_confidence: int = 3,
        min_near_signals_for_confidence: int = 1,
    ) -> dict[str, Any]:
        current = {
            "min_grab_drop_pct": float(current_profile.get("min_grab_drop_pct", 0.08)),
            "min_reclaim_bounce_pct": float(current_profile.get("min_reclaim_bounce_pct", 0.04)),
            "min_impulse_speed_pct_per_sec": float(current_profile.get("min_impulse_speed_pct_per_sec", 0.01)),
            "signal_min_score": float(current_profile.get("signal_min_score", 70)),
        }
        suggested = {
            "min_grab_drop_pct": float(suggested_profile.get("min_grab_drop_pct", current["min_grab_drop_pct"])),
            "min_reclaim_bounce_pct": float(suggested_profile.get("min_reclaim_bounce_pct", current["min_reclaim_bounce_pct"])),
            "min_impulse_speed_pct_per_sec": float(suggested_profile.get("min_impulse_speed_pct_per_sec", current["min_impulse_speed_pct_per_sec"])),
            "signal_min_score": float(suggested_profile.get("signal_min_score", current["signal_min_score"])),
        }

        def _pass_counts(profile: dict[str, float]) -> dict[str, int]:
            pass_drop = pass_bounce = pass_speed = near = 0
            blockers: Counter[str] = Counter()
            for e in self.events:
                drop_ok = float(e.get("drop_pct", 0.0)) >= profile["min_grab_drop_pct"]
                bounce_ok = float(e.get("bounce_pct", 0.0)) >= profile["min_reclaim_bounce_pct"]
                speed_ok = abs(float(e.get("speed", 0.0))) >= profile["min_impulse_speed_pct_per_sec"]
                score = float(e.get("score", 0.0))
                if drop_ok:
                    pass_drop += 1
                if bounce_ok:
                    pass_bounce += 1
                if speed_ok:
                    pass_speed += 1
                if drop_ok and bounce_ok and speed_ok and score >= profile["signal_min_score"] and not bool(e.get("detected", False)):
                    near += 1
                if score >= 50.0 and not bool(e.get("detected", False)):
                    if not drop_ok:
                        blockers["drop_ok"] += 1
                    elif not bounce_ok:
                        blockers["bounce_ok"] += 1
                    elif not speed_ok:
                        blockers["speed_ok"] += 1
            return {"pass_drop": pass_drop, "pass_bounce": pass_bounce, "pass_speed": pass_speed, "near": near, "blockers": dict(blockers)}

        current_stats = _pass_counts(current)
        suggested_stats = _pass_counts(suggested)
        raw_signals = sum(1 for e in self.events if str(e.get("signal", "")) == "LONG_SIGNAL" or bool(e.get("detected", False)))
        grouped_signals = len({int(e.get("signal_group_id", 0)) for e in self.events if int(e.get("signal_group_id", 0)) > 0})
        grade_counts = Counter(str(e.get("signal_quality_grade", e.get("signal_grade", ""))) for e in self.events if str(e.get("signal_quality_grade", e.get("signal_grade", ""))) in {"A_PLUS", "A", "B", "C", "TRASH"})
        closed_trades = [e for e in self.events if str(e.get("paper_trade_result", "")) in {"WIN", "LOSS", "TIMEOUT"}]
        pnls = [float(e.get("paper_trade_pnl_pct", 0.0)) for e in closed_trades]
        wins = sum(1 for e in closed_trades if e.get("paper_trade_result") == "WIN")
        losses = sum(1 for e in closed_trades if e.get("paper_trade_result") == "LOSS")
        timeouts = sum(1 for e in closed_trades if e.get("paper_trade_result") == "TIMEOUT")
        total_events = len(self.events)
        sweeps_found = sum(1 for e in self.events if str(e.get("phase", "")) == "LIQUIDITY_SWEEP")
        post = self.report_data.get("post_sweep_analysis", {})
        reclaim_wait = int(post.get("reclaim_wait_count", 0))
        hold_blockers = int((self.report_data.get("near_signal_blockers", {}) or {}).get("hold_ok", 0))
        detected_after_sweep = int(post.get("detected_after_sweep_count", 0))
        data_is_small = (
            total_events < min_research_ticks
            or sweeps_found < min_sweeps_for_confidence
        )
        delta_near = suggested_stats["near"] - current_stats["near"]
        too_soft = (
            suggested["min_grab_drop_pct"] < 0.003
            or suggested["min_reclaim_bounce_pct"] < 0.002
            or suggested["min_impulse_speed_pct_per_sec"] < 0.0003
        )
        if data_is_small:
            recommendation = "NEED_MORE_DATA"
            confidence = "LOW"
            reason = "insufficient session size or setup count"
        elif sweeps_found > 0 and reclaim_wait <= max(1, sweeps_found // 20) and delta_near <= 0:
            recommendation = "RECLAIM_WEAK"
            confidence = "MEDIUM"
            reason = "many sweeps but very few reclaim waits"
        elif reclaim_wait > 0 and detected_after_sweep == 0 and hold_blockers > 0:
            recommendation = "HOLD_TOO_STRICT"
            confidence = "HIGH"
            reason = "reclaim exists but HOLD blocks all signal candidates"
        elif reclaim_wait > 0 and detected_after_sweep == 0:
            recommendation = "FINAL_SIGNAL_BLOCKED"
            confidence = "MEDIUM"
            reason = "reclaim/hold path exists but no final signal detected"
        elif delta_near > 0 and not too_soft:
            recommendation = "APPLY_RECOMMENDED"
            confidence = "HIGH"
            reason = "near signals improved with non-extreme thresholds"
        else:
            recommendation = "DO_NOT_APPLY"
            confidence = "MEDIUM"
            reason = "no meaningful near-signal improvement"
        return {
            "current_profile": current_profile.get("name", "CURRENT"),
            "suggested_profile": suggested_profile.get("name", "CALIBRATED"),
            "total_events": total_events,
            "current_pass_drop": current_stats["pass_drop"],
            "suggested_pass_drop": suggested_stats["pass_drop"],
            "current_pass_bounce": current_stats["pass_bounce"],
            "suggested_pass_bounce": suggested_stats["pass_bounce"],
            "current_pass_speed": current_stats["pass_speed"],
            "suggested_pass_speed": suggested_stats["pass_speed"],
            "current_near_signal_count": current_stats["near"],
            "suggested_near_signal_count": suggested_stats["near"],
            "blockers_before": current_stats["blockers"],
            "blockers_after": suggested_stats["blockers"],
            "delta_near_signals": delta_near,
            "recommendation": recommendation,
            "confidence": confidence,
            "reason": reason,
            "auto_apply": False,
        }

    def _format_report(self, data: dict[str, Any]) -> str:
        def fmt_counter(counter_dict: dict[str, Any]) -> str:
            if not counter_dict:
                return "  - none"
            pairs = sorted(counter_dict.items(), key=lambda x: x[1], reverse=True)
            return "\n".join(f"  - {k}: {v}" for k, v in pairs)

        lines = ["bTest Session Analyzer Report", "=" * 32, "", "General:", f"  total_events: {data['total_events']}", f"  detected_count: {data['detected_count']}", f"  max_score: {data['max_score']:.2f}", f"  avg_score: {data['avg_score']:.2f}", "  profile_counts:", fmt_counter(data["profile_counts"]), "", "Phases:", fmt_counter(data["phase_counts"]), "", "Reason codes:", fmt_counter(data["reason_code_counts"]), "", "Fail counts (debug flags == false):", fmt_counter(data["fail_counts"]), "", "Near signals (score >= 50 and detected=false):", f"  count: {data['near_signals_count']}", "  blockers:", fmt_counter(data["near_signal_blockers"]), "  top20:"]
        if data["near_signal_top20"]:
            for item in data["near_signal_top20"]:
                lines.append(f"    ts={item['ts']} score={item['score']:.2f} phase={item['phase']} blocker={item['blocker']} profile={item['profile']} drop={item['drop_pct']:.5f} bounce={item['bounce_pct']:.5f} speed={item['speed']:.5f}")
        else:
            lines.append("    - none")

        hints = data["threshold_hints"]
        post = data.get("post_sweep_analysis", {})
        reclaim_hints = data.get("reclaim_hints", {})
        lines.extend(["", "Threshold hints:", f"  max_drop_pct: {hints['max_drop_pct']:.5f}", f"  p90_drop_pct: {hints['p90_drop_pct']:.5f}", f"  p95_drop_pct: {hints['p95_drop_pct']:.5f}", f"  max_bounce_pct: {hints['max_bounce_pct']:.5f}", f"  p90_bounce_pct: {hints['p90_bounce_pct']:.5f}", f"  p95_bounce_pct: {hints['p95_bounce_pct']:.5f}", f"  near_signal_bounce_p75: {hints['near_signal_bounce_p75']:.5f}", f"  near_signal_bounce_median: {hints['near_signal_bounce_median']:.5f}", f"  max_speed: {hints['max_speed']:.5f}", f"  p95_speed: {hints['p95_speed']:.5f}", f"  p75_abs_speed: {hints['p75_abs_speed']:.5f}", f"  pass_drop_ok: {hints['pass_drop_ok']}", f"  pass_drop_bounce: {hints['pass_drop_bounce']}", f"  pass_drop_bounce_reclaim: {hints['pass_drop_bounce_reclaim']}", f"  pass_hold_ok: {hints['pass_hold_ok']}"])

        suggested = data.get("suggested_profile") or self.suggest_profile()
        lines.extend(["", "=== SUGGESTED CALIBRATED PROFILE ===", f"Suggested drop={suggested['min_grab_drop_pct']:.3f}", f"Suggested bounce={suggested['min_reclaim_bounce_pct']:.3f}", f"Suggested speed={suggested['min_impulse_speed_pct_per_sec']:.3f}", f"Suggested score={suggested['signal_min_score']:.0f}", f"source p90 drop={hints['p90_drop_pct']:.5f}", f"source p95 drop={hints['p95_drop_pct']:.5f}", f"source p90 bounce={hints['p90_bounce_pct']:.5f}", f"source p95 bounce={hints['p95_bounce_pct']:.5f}", f"source near median bounce={hints['near_signal_bounce_median']:.5f}", f"source p75 abs speed={hints['p75_abs_speed']:.5f}", "Reasons:"])
        for reason in suggested.get("reason", []):
            lines.append(f"  - {reason}")
        validation = data.get("calibration_validation", {})
        if validation:
            lines.extend(
                [
                    "",
                    "CALIBRATION VALIDATION",
                    f"  current profile: {validation.get('current_profile', '-')}",
                    f"  suggested profile: {validation.get('suggested_profile', '-')}",
                    f"  total events: {validation.get('total_events', 0)}",
                    f"  pass drop before/after: {validation.get('current_pass_drop', 0)}/{validation.get('suggested_pass_drop', 0)}",
                    f"  pass bounce before/after: {validation.get('current_pass_bounce', 0)}/{validation.get('suggested_pass_bounce', 0)}",
                    f"  pass speed before/after: {validation.get('current_pass_speed', 0)}/{validation.get('suggested_pass_speed', 0)}",
                    f"  near signals before/after: {validation.get('current_near_signal_count', 0)}/{validation.get('suggested_near_signal_count', 0)}",
                    f"  blockers before: {validation.get('blockers_before', {})}",
                    f"  blockers after: {validation.get('blockers_after', {})}",
                    f"  recommendation: {validation.get('recommendation', '-')}",
                    f"  confidence: {validation.get('confidence', '-')}",
                    f"  reason: {validation.get('reason', '-')}",
                ]
            )

        sq = data.get("signal_quality_paper", {}) or {}
        lines.extend(["", "SIGNAL QUALITY", f"  raw_long_signals: {sq.get('raw_signals', 0)}", f"  market_events: {sq.get('market_events', 0)}", f"  duplicate_signals_suppressed: {sq.get('duplicate_signals_suppressed', 0)}", f"  grade_counts: {sq.get('grade_counts', {})}", f"  average quality score: {sq.get('average_quality_score', 0.0):.2f}", f"  top trash reasons: {sq.get('top_trash_reasons', {})}", f"  top downgrade reasons: {sq.get('top_downgrade_reasons', {})}", "", "SIGNAL QUALITY / PAPER SIMULATION", f"  paper trades: {sq.get('paper_trades', 0)}", f"  wins/losses/timeouts: {sq.get('wins', 0)}/{sq.get('losses', 0)}/{sq.get('timeouts', 0)}", f"  winrate: {sq.get('winrate', 0.0):.2f}%", f"  avg pnl: {sq.get('avg_pnl', 0.0):.4f}%", f"  total pnl: {sq.get('total_pnl', 0.0):.4f}%", f"  max favorable avg: {sq.get('max_favorable_avg', 0.0):.4f}%", f"  max adverse avg: {sq.get('max_adverse_avg', 0.0):.4f}%", f"  recommendation: {sq.get('recommendation', 'NEED_MORE_DATA')}"])

        lines.extend(["", "ADAPTIVE HOLD ANALYSIS", f"  detected_count: {(data.get('adaptive_hold_analysis', {}) or {}).get('detected_count', 0)}", f"  would_signal_count: {(data.get('adaptive_hold_analysis', {}) or {}).get('would_signal_count', 0)}", f"  hold_blocker_count: {(data.get('adaptive_hold_analysis', {}) or {}).get('hold_blocker_count', 0)}", f"  effective_hold_median: {(data.get('adaptive_hold_analysis', {}) or {}).get('effective_hold_median', 0.0):.2f}", f"  effective_hold_p75: {(data.get('adaptive_hold_analysis', {}) or {}).get('effective_hold_p75', 0.0):.2f}", f"  adaptive_hold_active_count: {(data.get('adaptive_hold_analysis', {}) or {}).get('adaptive_hold_active_count', 0)}", f"  detected_after_adaptive_hold: {(data.get('adaptive_hold_analysis', {}) or {}).get('detected_after_adaptive_hold', 0)}", f"  recommendation: {(data.get('adaptive_hold_analysis', {}) or {}).get('recommendation', 'NEED_MORE_DATA')}", "", "SIGNAL UNLOCK ANALYSIS", f"  would signals: {data.get('would_signal_count', 0)}", f"  would signals after sweep: {data.get('would_signal_after_sweep', 0)}", f"  would signal reasons: {data.get('would_signal_reasons', {})}", f"  would signal rate: {data.get('would_signal_rate', 0.0):.2f}%", f"  top unlock blockers: {(data.get('signal_unlock_analysis', {}) or {}).get('top_unlock_blockers', {})}", f"  avg would-signal score: {(data.get('signal_unlock_analysis', {}) or {}).get('avg_would_signal_score', 0.0):.2f}", f"  reclaim success before would-signal: {(data.get('signal_unlock_analysis', {}) or {}).get('reclaim_success_before_would_signal', 0.0):.2f}%", f"  recommendation: {(data.get('signal_unlock_analysis', {}) or {}).get('recommendation', 'STILL_NO_SIGNAL')}"])
        ba = data.get("bounce_reclaim_alignment_analysis", {}) or {}
        lines.extend(["", "BOUNCE / RECLAIM ALIGNMENT ANALYSIS", f"  base bounce threshold: {ba.get('base_bounce_threshold', 0.0):.5f}", f"  effective bounce threshold median/p75: {ba.get('effective_bounce_threshold_median', 0.0):.5f}/{ba.get('effective_bounce_threshold_p75', 0.0):.5f}", f"  reclaim distance median/p75: {ba.get('reclaim_distance_median_pct', 0.0):.5f}/{ba.get('reclaim_distance_p75_pct', 0.0):.5f}", f"  bounce blocker count: {ba.get('bounce_blocker_count', 0)}", f"  reclaim blocker count: {ba.get('reclaim_blocker_count', 0)}", f"  would_signal_bounce count: {ba.get('would_signal_bounce_count', 0)}", f"  would_signal_hold count: {ba.get('would_signal_hold_count', 0)}", f"  detected count: {ba.get('detected_count', 0)}", f"  recommendation: {ba.get('recommendation', 'READY_FOR_SIGNAL_QUALITY')}"])
        lines.extend(
            [
                "",
                "POST-SWEEP RECLAIM/HOLD ANALYSIS",
                f"  total sweeps: {post.get('total_sweeps', 0)}",
                f"  reclaim wait count: {post.get('reclaim_wait_count', 0)}",
                f"  invalidated after sweep: {post.get('invalidated_after_sweep_count', 0)}",
                f"  detected after sweep: {post.get('detected_after_sweep_count', 0)}",
                f"  reclaim success rate: {post.get('reclaim_success_rate', 0.0):.2f}%",
                f"  signal success rate: {post.get('signal_success_rate', 0.0):.2f}%",
                f"  median/p75 setup age ms: {post.get('median_setup_age_ms', 0.0):.2f}/{post.get('p75_setup_age_ms', 0.0):.2f}",
                f"  median/p75 reclaim hold ms: {post.get('median_reclaim_hold_ms', 0.0):.2f}/{post.get('p75_reclaim_hold_ms', 0.0):.2f}",
                f"  top invalidation reasons: {post.get('top_invalidation_reasons', {})}",
                f"  top blockers after sweep: {post.get('top_blockers_after_sweep', {})}",
                f"  suggested min reclaim hold ms: {reclaim_hints.get('suggested_min_reclaim_hold_ms', 150)}",
                f"  suggested reclaim window ms: {reclaim_hints.get('suggested_reclaim_window_ms', 3000)}",
                f"  suggested invalidation cooldown ms: {reclaim_hints.get('suggested_invalidation_cooldown_ms', 1000)}",
                f"  conclusion: {validation.get('recommendation', 'NEED_MORE_DATA') if validation else 'NEED_MORE_DATA'}",
            ]
        )
        return "\n".join(lines) + "\n"

    def export_report(self, path: str | Path) -> Path:
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.report_text:
            self.analyze()
        report_path.write_text(self.report_text, encoding="utf-8")
        return report_path
