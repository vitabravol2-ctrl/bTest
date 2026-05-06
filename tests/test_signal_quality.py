from app.session_analyzer import SessionAnalyzer
from app.signal_quality import SignalQualityEngine
from app.signals import LiquidityGrabSignal


def mk_signal(ts: int, score: float, **kw):
    return LiquidityGrabSignal(
        detected=True, side="LONG", score=score, phase="LONG_SIGNAL", trigger_price=100.0,
        reason_codes=kw.get("reasons", ["RECLAIM_CONFIRMED"]), ts_ms=ts,
        reclaim_distance_pct=kw.get("reclaim_distance_pct", 0.01), bounce_ok_effective=kw.get("bounce_ok_effective", True),
        reclaim_hold_ms=kw.get("reclaim_hold_ms", 300), effective_hold_ms=kw.get("effective_hold_ms", 200), setup_age_ms=kw.get("setup_age_ms", 1000),
        debug={"slow_trend_ok": True},
    )


def test_grades_and_trash():
    e = SignalQualityEngine(55)
    assert e.evaluate(mk_signal(1000, 95), True, True).grade == "A_PLUS"
    assert e.evaluate(mk_signal(50000, 82), True, True).grade == "A"
    assert e.evaluate(mk_signal(90000, 72), True, False).grade == "B"
    assert e.evaluate(mk_signal(130000, 56), True, False).grade == "C"
    assert e.evaluate(mk_signal(170000, 90, setup_age_ms=9000), True, True).grade == "TRASH"


def test_duplicate_cluster_logic():
    e = SignalQualityEngine(55)
    q1 = e.evaluate(mk_signal(1000, 90), True, True)
    q2 = e.evaluate(mk_signal(2000, 92), True, True)
    assert q1.is_new_market_event is True
    assert q2.is_duplicate_signal is True
    assert q1.signal_cluster_id == q2.signal_cluster_id


def test_old_jsonl_backward_compatible(tmp_path):
    p = tmp_path / "old.jsonl"
    p.write_text('{"signal":"LONG_SIGNAL","detected":true,"score":80,"phase":"LONG_SIGNAL","debug":{}}\n', encoding="utf-8")
    a = SessionAnalyzer(); a.load(p); data = a.analyze()
    assert data["total_events"] == 1
