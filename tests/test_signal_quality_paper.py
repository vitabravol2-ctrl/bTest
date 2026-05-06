from app.paper_simulator import PaperSimulator
from app.signal_quality import SignalQualityEngine
from app.signals import LiquidityGrabSignal
from app.session_analyzer import SessionAnalyzer


def mk_signal(ts, score, reasons=None):
    return LiquidityGrabSignal(detected=True, side="LONG", score=score, phase="LONG_SIGNAL", trigger_price=100.0, reason_codes=reasons or ["RECLAIM_CONFIRMED"], ts_ms=ts)


def test_signal_grouping_reduces_spam_signals():
    e = SignalQualityEngine(signal_min_score=70)
    q1 = e.evaluate(mk_signal(1000, 85), True, True)
    q2 = e.evaluate(mk_signal(2000, 84), True, True)
    assert q1 and q2
    assert e.raw_signal_count == 2
    assert e.grouped_signal_count == 1


def test_signal_quality_grades_a_b_c():
    e = SignalQualityEngine(signal_min_score=70)
    assert e.evaluate(mk_signal(1000, 95), True, True).grade == "A"
    assert e.evaluate(mk_signal(7000, 85), True, False).grade == "TRASH"
    assert e.evaluate(mk_signal(13000, 72), True, False).grade == "TRASH"


def test_paper_trade_hits_take_profit():
    p = PaperSimulator(take_profit_pct=0.03, stop_loss_pct=0.02, max_hold_seconds=30)
    p.open_long(0, 100)
    t = p.on_tick(1000, 0, 103)
    assert t and t.result == "WIN"


def test_paper_trade_hits_stop_loss():
    p = PaperSimulator()
    p.open_long(0, 100)
    t = p.on_tick(1000, 0, 98)
    assert t and t.result == "LOSS"


def test_paper_trade_timeout():
    p = PaperSimulator(max_hold_seconds=1)
    p.open_long(0, 100)
    t = p.on_tick(1500, 0, 100)
    assert t and t.result == "TIMEOUT"


def test_paper_simulator_does_not_import_binance_execution():
    content = open('app/paper_simulator.py', encoding='utf-8').read().lower()
    assert 'binance' not in content
    assert 'buy(' not in content
    assert 'sell(' not in content


def test_report_contains_signal_quality_paper_section(tmp_path):
    p = tmp_path / 's.jsonl'
    p.write_text('{"signal":"LONG_SIGNAL","detected":true,"signal_group_id":1,"signal_grade":"A","paper_trade_result":"WIN","score":91,"phase":"LONG_SIGNAL","debug":{}}\n', encoding='utf-8')
    a = SessionAnalyzer(); a.load(p); a.analyze()
    assert 'SIGNAL QUALITY / PAPER SIMULATION' in a.report_text
