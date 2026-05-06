import json

from app.session_analyzer import SessionAnalyzer


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_empty_file(tmp_path):
    p = tmp_path / "session_empty.jsonl"
    p.write_text("", encoding="utf-8")

    analyzer = SessionAnalyzer()
    analyzer.load(p)
    data = analyzer.analyze()

    assert data["total_events"] == 0
    assert data["detected_count"] == 0
    assert data["max_score"] == 0.0


def test_simple_no_signal_session(tmp_path):
    p = tmp_path / "session_no_signal.jsonl"
    write_jsonl(
        p,
        [
            {
                "ts": 1,
                "score": 52,
                "detected": False,
                "phase": "WATCHING_DROP",
                "reason_codes": ["DROP_NOT_DEEP_ENOUGH"],
                "debug": {"drop_ok": False, "bounce_ok": False, "speed_ok": True, "reclaim_ok": False, "hold_ok": False, "slow_trend_ok": True},
            }
        ],
    )

    analyzer = SessionAnalyzer()
    analyzer.load(p)
    data = analyzer.analyze()

    assert data["near_signals_count"] == 1
    assert data["near_signal_blockers"]["drop_ok"] == 1


def test_profile_counts_and_fail_counts(tmp_path):
    p = tmp_path / "session_profiles.jsonl"
    write_jsonl(
        p,
        [
            {"score": 10, "detected": False, "profile_name": "CONSERVATIVE", "phase": "NO_SETUP", "debug": {"drop_ok": False}},
            {"score": 20, "detected": False, "profile_name": "SENSITIVE", "phase": "WATCHING_DROP", "debug": {"drop_ok": True, "bounce_ok": False}},
            {"score": 80, "detected": True, "profile_name": "SENSITIVE", "phase": "RECLAIM_WAIT", "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": True, "slow_trend_ok": True}},
        ],
    )

    analyzer = SessionAnalyzer()
    analyzer.load(p)
    data = analyzer.analyze()

    assert data["profile_counts"]["SENSITIVE"] == 2
    assert data["profile_counts"]["CONSERVATIVE"] == 1
    assert data["fail_counts"]["drop_ok"] == 1
    assert data["fail_counts"]["bounce_ok"] >= 1


def test_report_export_creates_file(tmp_path):
    p = tmp_path / "session_export.jsonl"
    write_jsonl(p, [{"score": 1, "detected": False, "phase": "NO_SETUP", "debug": {}}])

    analyzer = SessionAnalyzer()
    analyzer.load(p)
    analyzer.analyze()

    report_path = tmp_path / "session_export_report.txt"
    analyzer.export_report(report_path)

    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "total_events" in text


def test_analyze_calls_suggest_once_cleanly(tmp_path, monkeypatch):
    p = tmp_path / "session_once.jsonl"
    write_jsonl(p, [{"score": 52, "detected": False, "drop_pct": 0.02, "bounce_pct": 0.01, "speed": -0.002, "debug": {"drop_ok": False}}])

    analyzer = SessionAnalyzer()
    analyzer.load(p)

    calls = {"count": 0}
    original = SessionAnalyzer.suggest_profile

    def wrapped(self):
        calls["count"] += 1
        return original(self)

    monkeypatch.setattr(SessionAnalyzer, "suggest_profile", wrapped)
    data = analyzer.analyze()

    assert calls["count"] == 1
    assert data["suggested_profile"]["name"] == "CALIBRATED"


def test_validation_recommends_apply_when_near_signals_improve(tmp_path):
    p = tmp_path / "session_validation_apply.jsonl"
    rows = []
    for i in range(305):
        rows.append({"ts": i, "phase": "LIQUIDITY_SWEEP" if i < 4 else "WATCHING_DROP", "drop_pct": 0.03, "bounce_pct": 0.02, "speed": 0.003, "score": 62, "detected": False, "debug": {}})
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    suggested = {"name": "CALIBRATED", "min_grab_drop_pct": 0.02, "min_reclaim_bounce_pct": 0.01, "min_impulse_speed_pct_per_sec": 0.002, "signal_min_score": 55}
    current = {"name": "CONSERVATIVE", "min_grab_drop_pct": 0.08, "min_reclaim_bounce_pct": 0.04, "min_impulse_speed_pct_per_sec": 0.01, "signal_min_score": 70}
    result = analyzer.validate_calibration_before_after(current, suggested)
    assert result["recommendation"] == "APPLY_RECOMMENDED"
    assert result["delta_near_signals"] > 0


def test_validation_needs_more_data_when_session_too_small(tmp_path):
    p = tmp_path / "session_small.jsonl"
    write_jsonl(p, [{"drop_pct": 0.04, "bounce_pct": 0.03, "speed": 0.004, "score": 61, "detected": False, "phase": "WATCHING_DROP"} for _ in range(10)])
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    current = {"name": "CUSTOM", "min_grab_drop_pct": 0.01, "min_reclaim_bounce_pct": 0.01, "min_impulse_speed_pct_per_sec": 0.001, "signal_min_score": 70}
    result = analyzer.validate_calibration_before_after(current, {"name": "CALIBRATED"})
    assert result["recommendation"] == "NEED_MORE_DATA"
    assert result["confidence"] == "LOW"


def test_validation_does_not_auto_apply_profile(tmp_path):
    p = tmp_path / "session_auto_apply.jsonl"
    write_jsonl(p, [{"drop_pct": 0.04, "bounce_pct": 0.03, "speed": 0.004, "score": 61, "detected": False, "phase": "WATCHING_DROP"} for _ in range(320)])
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    current = {"name": "CUSTOM", "min_grab_drop_pct": 0.01, "min_reclaim_bounce_pct": 0.01, "min_impulse_speed_pct_per_sec": 0.001, "signal_min_score": 70}
    result = analyzer.validate_calibration_before_after(current, {"name": "CALIBRATED"})
    assert result["auto_apply"] is False


def test_report_contains_calibration_validation_section(tmp_path):
    p = tmp_path / "session_report_validation.jsonl"
    write_jsonl(p, [{"drop_pct": 0.01, "bounce_pct": 0.01, "speed": 0.002, "score": 52, "detected": False, "phase": "WATCHING_DROP", "debug": {"drop_ok": False}} for _ in range(20)])
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    analyzer.analyze()
    assert "CALIBRATION VALIDATION" in analyzer.report_text


def test_post_sweep_analysis_counts_sweeps_and_reclaims(tmp_path):
    p = tmp_path / "session_post_sweep.jsonl"
    write_jsonl(
        p,
        [
            {"phase": "LIQUIDITY_SWEEP", "score": 30, "detected": False, "setup_age_ms": 1000, "reclaim_hold_ms": 0, "debug": {}},
            {"phase": "RECLAIM_WAIT", "score": 60, "detected": False, "setup_age_ms": 1200, "reclaim_hold_ms": 200, "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}},
            {"phase": "INVALIDATED", "score": 40, "detected": False, "last_invalid_reason": "HOLD_TIMEOUT", "setup_age_ms": 1300, "reclaim_hold_ms": 300, "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}},
        ],
    )
    analyzer = SessionAnalyzer(); analyzer.load(p); data = analyzer.analyze()
    post = data["post_sweep_analysis"]
    assert post["total_sweeps"] == 1
    assert post["reclaim_wait_count"] == 1
    assert post["invalidated_after_sweep_count"] == 1


def test_reclaim_hold_hints_use_p75(tmp_path):
    p = tmp_path / "session_reclaim_hints.jsonl"
    write_jsonl(p, [{"phase": "RECLAIM_WAIT", "score": 10, "detected": False, "reclaim_hold_ms": v, "setup_age_ms": 1000 + v, "debug": {}} for v in [100, 200, 300, 400]])
    analyzer = SessionAnalyzer(); analyzer.load(p); data = analyzer.analyze()
    assert data["reclaim_hints"]["suggested_min_reclaim_hold_ms"] == int(300 * 0.70)


def test_report_contains_post_sweep_section(tmp_path):
    p = tmp_path / "session_report_post_sweep.jsonl"
    write_jsonl(p, [{"phase": "LIQUIDITY_SWEEP", "score": 10, "detected": False, "debug": {}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    assert "POST-SWEEP RECLAIM/HOLD ANALYSIS" in analyzer.report_text


def test_validation_detects_hold_too_strict(tmp_path):
    p = tmp_path / "session_hold_strict.jsonl"
    rows = [{"phase": "LIQUIDITY_SWEEP", "drop_pct": 0.05, "bounce_pct": 0.03, "speed": 0.005, "score": 55, "detected": False, "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}} for _ in range(320)]
    rows += [{"phase": "RECLAIM_WAIT", "drop_pct": 0.05, "bounce_pct": 0.03, "speed": 0.005, "score": 58, "detected": False, "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}} for _ in range(20)]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    current = {"name": "CUSTOM", "min_grab_drop_pct": 0.01, "min_reclaim_bounce_pct": 0.01, "min_impulse_speed_pct_per_sec": 0.001, "signal_min_score": 70}
    result = analyzer.validate_calibration_before_after(current, {"name": "CALIBRATED"})
    assert result["recommendation"] == "HOLD_TOO_STRICT"

def test_report_contains_signal_unlock_analysis(tmp_path):
    p = tmp_path / "session_unlock_report.jsonl"
    write_jsonl(p, [{"score": 80, "detected": False, "would_signal": True, "would_signal_reason": "WOULD_SIGNAL_HOLD", "phase": "RECLAIM_WAIT", "reason_codes": ["SWEEP_FOUND"], "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    assert "SIGNAL UNLOCK ANALYSIS" in analyzer.report_text
    assert analyzer.report_data["would_signal_count"] == 1

def test_report_contains_adaptive_hold_analysis(tmp_path):
    p = tmp_path / "session_adaptive_hold.jsonl"
    write_jsonl(p, [{"score": 80, "detected": False, "would_signal": True, "phase": "RECLAIM_WAIT", "effective_hold_ms": 400, "base_hold_ms": 1500, "adaptive_hold_active": True, "debug": {"drop_ok": True, "bounce_ok": True, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    assert "ADAPTIVE HOLD ANALYSIS" in analyzer.report_text


def test_report_contains_bounce_reclaim_alignment_analysis(tmp_path):
    p = tmp_path / "session_bounce_reclaim_alignment.jsonl"
    write_jsonl(p, [{"score": 80, "detected": False, "would_signal": True, "would_signal_reason": "WOULD_SIGNAL_BOUNCE", "phase": "RECLAIM_WAIT", "effective_bounce_threshold": 0.003, "reclaim_distance_pct": 0.02, "thresholds": {"min_reclaim_bounce_pct": 0.01}, "debug": {"drop_ok": True, "bounce_ok": False, "speed_ok": True, "reclaim_ok": True, "hold_ok": False, "slow_trend_ok": True}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    assert "BOUNCE / RECLAIM ALIGNMENT ANALYSIS" in analyzer.report_text
