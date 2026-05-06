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
    result = analyzer.validate_calibration_before_after({}, {"name": "CALIBRATED"})
    assert result["recommendation"] == "NEED_MORE_DATA"
    assert result["confidence"] == "LOW"


def test_validation_does_not_auto_apply_profile(tmp_path):
    p = tmp_path / "session_auto_apply.jsonl"
    write_jsonl(p, [{"drop_pct": 0.04, "bounce_pct": 0.03, "speed": 0.004, "score": 61, "detected": False, "phase": "WATCHING_DROP"} for _ in range(320)])
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    result = analyzer.validate_calibration_before_after({}, {"name": "CALIBRATED"})
    assert result["auto_apply"] is False


def test_report_contains_calibration_validation_section(tmp_path):
    p = tmp_path / "session_report_validation.jsonl"
    write_jsonl(p, [{"drop_pct": 0.01, "bounce_pct": 0.01, "speed": 0.002, "score": 52, "detected": False, "phase": "WATCHING_DROP", "debug": {"drop_ok": False}} for _ in range(20)])
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    analyzer.analyze()
    assert "CALIBRATION VALIDATION" in analyzer.report_text
