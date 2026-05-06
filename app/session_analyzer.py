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

    def suggest_profile(self) -> dict[str, Any]:
        if not self.report_data:
            self.analyze()
        hints = self.report_data.get("threshold_hints", {})
        near_signals_count = int(self.report_data.get("near_signals_count", 0))

        p95_drop_pct = float(hints.get("p95_drop_pct", 0.0))
        all_bounce_p95 = float(hints.get("p95_bounce_pct", 0.0))
        near_signal_bounce_p75 = float(hints.get("near_signal_bounce_p75", 0.0))
        near_signal_bounce_median = float(hints.get("near_signal_bounce_median", 0.0))
        p75_abs_speed = float(hints.get("p75_abs_speed", 0.0))
        max_bounce = float(hints.get("max_bounce_pct", 0.0))

        if near_signals_count > 0:
            near_median_component = near_signal_bounce_median * 0.80 if near_signal_bounce_median > 0 else all_bounce_p95 * 0.55
            min_reclaim_bounce_pct = max(0.003, min(all_bounce_p95 * 0.55, near_median_component))
        else:
            min_reclaim_bounce_pct = max(0.003, all_bounce_p95 * 0.50)

        suggested = {
            "name": "CALIBRATED",
            "min_grab_drop_pct": max(0.005, p95_drop_pct * 0.70),
            "min_reclaim_bounce_pct": min_reclaim_bounce_pct,
            "min_impulse_speed_pct_per_sec": max(0.0005, p75_abs_speed * 0.60),
            "signal_min_score": 55 if near_signals_count > 0 else 60,
            "max_trend_drop_mid_pct": 0.25,
            "max_slow_trend_drop_pct": 0.40,
            "reason": [
                "bounce threshold softened to avoid overblocking",
                "drop threshold uses p95*0.70",
                "speed uses p75 abs speed",
                f"p95_drop_pct={p95_drop_pct:.5f}",
                f"all_bounce_p95={all_bounce_p95:.5f}",
                f"near_signal_bounce_p75={near_signal_bounce_p75:.5f}",
                f"near_signal_bounce_median={near_signal_bounce_median:.5f}",
                f"p75_abs_speed={p75_abs_speed:.5f}",
                f"max_bounce_pct={max_bounce:.5f}",
                f"near_signals_count={near_signals_count}",
                f"near_signal_blockers={self.report_data.get('near_signal_blockers', {})}",
                f"pass_drop_ok={hints.get('pass_drop_ok', 0)} pass_drop_bounce={hints.get('pass_drop_bounce', 0)}",
                f"pass_drop_bounce_reclaim={hints.get('pass_drop_bounce_reclaim', 0)} pass_hold_ok={hints.get('pass_hold_ok', 0)}",
                f"max_drop_pct={hints.get('max_drop_pct', 0.0):.5f}",
            ],
        }
        return suggested

    def analyze(self) -> dict[str, Any]:
        scores = [float(e.get("score", 0.0)) for e in self.events]
        detected_count = sum(1 for e in self.events if bool(e.get("detected", False)))

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

        data = {
            "total_events": len(self.events),
            "detected_count": detected_count,
            "max_score": max(scores) if scores else 0.0,
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
                "p95_drop_pct": self._p95(drop_values),
                "max_bounce_pct": max(bounce_values) if bounce_values else 0.0,
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
        }
        self.report_data = data
        suggested = self.suggest_profile()
        data["suggested_profile"] = suggested
        self.report_data = data
        self.report_text = self._format_report(data)
        return data

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
        lines.extend(["", "Threshold hints:", f"  max_drop_pct: {hints['max_drop_pct']:.5f}", f"  p95_drop_pct: {hints['p95_drop_pct']:.5f}", f"  max_bounce_pct: {hints['max_bounce_pct']:.5f}", f"  p95_bounce_pct: {hints['p95_bounce_pct']:.5f}", f"  near_signal_bounce_p75: {hints['near_signal_bounce_p75']:.5f}", f"  near_signal_bounce_median: {hints['near_signal_bounce_median']:.5f}", f"  max_speed: {hints['max_speed']:.5f}", f"  p95_speed: {hints['p95_speed']:.5f}", f"  p75_abs_speed: {hints['p75_abs_speed']:.5f}", f"  pass_drop_ok: {hints['pass_drop_ok']}", f"  pass_drop_bounce: {hints['pass_drop_bounce']}", f"  pass_drop_bounce_reclaim: {hints['pass_drop_bounce_reclaim']}", f"  pass_hold_ok: {hints['pass_hold_ok']}"])

        suggested = data.get("suggested_profile") or self.suggest_profile()
        lines.extend(["", "=== SUGGESTED CALIBRATED PROFILE ===", f"Suggested drop={suggested['min_grab_drop_pct']:.3f}", f"Suggested bounce={suggested['min_reclaim_bounce_pct']:.3f}", f"Suggested speed={suggested['min_impulse_speed_pct_per_sec']:.3f}", f"Suggested score={suggested['signal_min_score']:.0f}", f"source p95 drop={hints['p95_drop_pct']:.5f}", f"source p95 bounce={hints['p95_bounce_pct']:.5f}", f"source near median bounce={hints['near_signal_bounce_median']:.5f}", f"source p75 abs speed={hints['p75_abs_speed']:.5f}", "Reasons:"])
        for reason in suggested.get("reason", []):
            lines.append(f"  - {reason}")
        return "\n".join(lines) + "\n"

    def export_report(self, path: str | Path) -> Path:
        report_path = Path(path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.report_text:
            self.analyze()
        report_path.write_text(self.report_text, encoding="utf-8")
        return report_path
