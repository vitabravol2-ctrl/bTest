import json

from app.session_analyzer import SessionAnalyzer


def test_paper_plan_preview_and_enriched_fields(tmp_path):
    events = [
        {"is_new_market_event": True, "is_duplicate_signal": False, "detected": True, "signal_quality_grade": "A_PLUS", "trigger_price": 100.0, "ts_ms": 1000},
        {"is_new_market_event": True, "is_duplicate_signal": True, "detected": True, "signal_quality_grade": "A", "trigger_price": 101.0, "ts_ms": 2000},
        {"is_new_market_event": True, "is_duplicate_signal": False, "detected": False, "signal_quality_grade": "A", "trigger_price": 102.0, "ts_ms": 3000},
        {"is_new_market_event": False, "detected": False, "ts_ms": 4000},
    ]
    p = tmp_path / "s.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    sa = SessionAnalyzer()
    sa.load(p)
    data = sa.analyze()
    prev = data["paper_plan_preview"]
    assert prev["planned_count"] == 1
    assert prev["skipped_count"] == 1
    assert prev["invalid_count"] == 1

    enriched = [json.loads(line) for line in (tmp_path / "s_enriched.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "paper_plan_status" in enriched[0]
    assert enriched[3]["paper_plan_status"] == ""
    assert enriched[3]["paper_plan_reason_codes"] == []
