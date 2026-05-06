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
