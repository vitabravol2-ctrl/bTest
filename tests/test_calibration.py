import json

import pytest

from app.calibration import CalibrationSuggestion
from app.session_analyzer import SessionAnalyzer


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_suggest_profile_empty_session(tmp_path):
    p = tmp_path / "session_empty.jsonl"
    p.write_text("", encoding="utf-8")
    analyzer = SessionAnalyzer()
    analyzer.load(p)
    analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["name"] == "CALIBRATED"
    assert suggested["min_grab_drop_pct"] == 0.005
    assert suggested["signal_min_score"] == 60


def test_suggest_profile_does_not_overraise_bounce(tmp_path):
    p = tmp_path / "session_vals.jsonl"
    rows = [
        {"drop_pct": 0.01, "bounce_pct": 0.010, "speed": -0.002, "score": 51, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.02, "bounce_pct": 0.020, "speed": -0.003, "score": 52, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.03, "bounce_pct": 0.030, "speed": -0.004, "score": 53, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.04, "bounce_pct": 0.040, "speed": -0.005, "score": 54, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.05, "bounce_pct": 0.050, "speed": -0.006, "score": 10, "detected": False, "debug": {}},
    ]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); data = analyzer.analyze()
    suggested = analyzer.suggest_profile()
    p95_bounce = data["threshold_hints"]["p95_bounce_pct"]
    assert suggested["min_reclaim_bounce_pct"] <= p95_bounce * 0.55


def test_suggest_profile_uses_p90_drop_formula(tmp_path):
    p = tmp_path / "session_p90_drop.jsonl"
    rows = [{"drop_pct": v, "bounce_pct": 0.01, "speed": 0.002, "score": 10, "detected": False, "debug": {}} for v in [0.001, 0.010, 0.020, 0.030, 0.040]]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_grab_drop_pct"] == max(0.005, 0.030 * 0.70)


def test_suggest_profile_uses_p90_bounce_formula(tmp_path):
    p = tmp_path / "session_p90_bounce.jsonl"
    rows = [
        {"drop_pct": 0.02, "bounce_pct": 0.005, "speed": 0.002, "score": 50, "detected": False, "debug": {}},
        {"drop_pct": 0.02, "bounce_pct": 0.010, "speed": 0.002, "score": 51, "detected": False, "debug": {}},
        {"drop_pct": 0.02, "bounce_pct": 0.020, "speed": 0.002, "score": 52, "detected": False, "debug": {}},
        {"drop_pct": 0.02, "bounce_pct": 0.030, "speed": 0.002, "score": 53, "detected": False, "debug": {}},
    ]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_reclaim_bounce_pct"] == pytest.approx(0.011)


def test_suggest_profile_upper_clamp_prevents_overblocking(tmp_path):
    p = tmp_path / "session_clamp.jsonl"
    rows = [{"drop_pct": v, "bounce_pct": v, "speed": 0.002, "score": 10, "detected": False, "debug": {}} for v in [0.001, 0.002, 0.5, 1.0]]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    hints = analyzer.report_data["threshold_hints"]
    assert suggested["min_grab_drop_pct"] <= hints["p95_drop_pct"] * 0.70
    assert suggested["min_reclaim_bounce_pct"] <= hints["p95_bounce_pct"] * 0.55


def test_suggest_profile_uses_near_signal_bounce_median(tmp_path):
    p = tmp_path / "session_near_median.jsonl"
    rows = [
        {"drop_pct": 0.03, "bounce_pct": 0.006, "speed": -0.004, "score": 50, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.03, "bounce_pct": 0.010, "speed": -0.004, "score": 51, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.03, "bounce_pct": 0.014, "speed": -0.004, "score": 52, "detected": False, "debug": {"drop_ok": True, "bounce_ok": False}},
        {"drop_pct": 0.03, "bounce_pct": 0.080, "speed": -0.004, "score": 10, "detected": False, "debug": {}},
    ]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_reclaim_bounce_pct"] == max(0.003, min(0.014 * 0.55, 0.010 * 0.80))


def test_suggest_profile_uses_p75_abs_speed(tmp_path):
    p = tmp_path / "session_speed.jsonl"
    write_jsonl(
        p,
        [
            {"drop_pct": 0.1, "bounce_pct": 0.1, "speed": -0.010, "score": 10, "detected": False, "debug": {}},
            {"drop_pct": 0.1, "bounce_pct": 0.1, "speed": -0.020, "score": 10, "detected": False, "debug": {}},
            {"drop_pct": 0.1, "bounce_pct": 0.1, "speed": 0.030, "score": 10, "detected": False, "debug": {}},
            {"drop_pct": 0.0, "bounce_pct": 0.1, "speed": 0.500, "score": 10, "detected": False, "debug": {}},
        ],
    )
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_impulse_speed_pct_per_sec"] == max(0.0005, 0.020 * 0.60)


def test_suggest_profile_to_threshold_profile():
    suggestion = CalibrationSuggestion("CALIBRATED", 0.01, 0.004, 0.002, 0.25, 0.4, 55, ["a"])
    profile = suggestion.to_profile()
    assert profile.name == "CALIBRATED"
    assert profile.min_grab_drop_pct == 0.01


def test_report_contains_suggested_calibrated_profile(tmp_path):
    p = tmp_path / "session_report.jsonl"
    write_jsonl(p, [{"drop_pct": 0.02, "bounce_pct": 0.01, "speed": 0.005, "score": 52, "detected": False, "debug": {"drop_ok": False}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    text = analyzer.report_text
    assert "=== SUGGESTED CALIBRATED PROFILE ===" in text
    assert "Suggested drop=" in text
    assert "source p95 drop=" in text
    assert "source near median bounce=" in text
