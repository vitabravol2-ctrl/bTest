import json

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


def test_suggest_profile_uses_p95_drop_bounce_speed(tmp_path):
    p = tmp_path / "session_vals.jsonl"
    rows = [{"drop_pct": d, "bounce_pct": b, "speed": s, "score": 10, "detected": False, "debug": {}} for d, b, s in [(0.01,0.005,0.002),(0.02,0.007,0.003),(0.03,0.009,0.004),(0.04,0.011,0.005),(0.05,0.013,0.006)]]
    write_jsonl(p, rows)
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_grab_drop_pct"] == max(0.005, 0.04 * 0.8)
    assert suggested["min_reclaim_bounce_pct"] == max(0.003, 0.011 * 0.8)
    assert suggested["min_impulse_speed_pct_per_sec"] == max(0.0005, 0.005 * 0.7)


def test_suggest_profile_abs_speed(tmp_path):
    p = tmp_path / "session_speed.jsonl"
    write_jsonl(p, [{"drop_pct": 0.1, "bounce_pct": 0.1, "speed": -0.01, "score": 10, "detected": False, "debug": {}}])
    analyzer = SessionAnalyzer(); analyzer.load(p); analyzer.analyze()
    suggested = analyzer.suggest_profile()
    assert suggested["min_impulse_speed_pct_per_sec"] == max(0.0005, abs(-0.01) * 0.7)


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
