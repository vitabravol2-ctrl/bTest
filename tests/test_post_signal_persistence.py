import json
from app.session_analyzer import SessionAnalyzer


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_post_signal_persistence(tmp_path):
    session = tmp_path / "session_x.jsonl"
    rows = [
        {"is_new_market_event": False, "ts_ms": 1000},
        {"is_new_market_event": True, "detected": True, "signal_quality_grade": "A", "last_price": 100.0, "ts_ms": 2000},
        {"is_new_market_event": True, "last_price": 101.0, "ts_ms": 3000},
        {"is_new_market_event": True, "last_price": 102.0, "ts_ms": 5000},
        {"is_new_market_event": True, "last_price": 103.0, "ts_ms": 7000},
    ]
    _write(session, rows)
    original = session.read_text(encoding="utf-8")

    analyzer = SessionAnalyzer()
    analyzer.load(session)
    data = analyzer.analyze()

    enriched = tmp_path / "session_x_enriched.jsonl"
    assert enriched.exists()
    assert session.read_text(encoding="utf-8") == original

    out_rows = [json.loads(x) for x in enriched.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert out_rows[0]["post_signal_calculated"] is False
    assert out_rows[0]["post_1s_return_pct"] == 0.0

    market = out_rows[1]
    assert market["post_signal_calculated"] is True
    assert market["post_signal_reference_price"] == 100.0
    assert market["post_1s_return_pct"] > 0

    assert data["post_signal_calculated_count"] >= 1


def test_missing_price_and_insufficient_future_data(tmp_path):
    session = tmp_path / "session_y.jsonl"
    rows = [
        {"is_new_market_event": True, "detected": True, "signal_quality_grade": "A", "ts_ms": 1000},
        {"is_new_market_event": True, "last_price": 100.0, "ts_ms": 1500},
    ]
    _write(session, rows)
    analyzer = SessionAnalyzer()
    analyzer.load(session)
    data = analyzer.analyze()
    assert data["post_signal_missing_price_count"] >= 1
    assert data["post_signal_insufficient_future_data_count"] >= 1
