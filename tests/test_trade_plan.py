from app.paper_engine import PaperEngine
from app.trade_plan import PLANNED, SKIPPED, TradePlan


def _event(**kwargs):
    base = {
        "is_new_market_event": True,
        "is_duplicate_signal": False,
        "detected": True,
        "signal_quality_grade": "A_PLUS",
        "trigger_price": 100.0,
        "ts_ms": 1,
    }
    base.update(kwargs)
    return base


def test_trade_plan_dataclass_created():
    tp = TradePlan(1, 2, "BTCUSDT", "LONG", "A", 80.0, 100.0, 1, "MARKET", 100.0, 0.05, 0.03, 12000, PLANNED, [])
    assert tp.symbol == "BTCUSDT"


def test_grades_and_skip_logic():
    pe = PaperEngine()
    assert pe.build_trade_plan(_event(signal_quality_grade="A_PLUS")).tp_pct == 0.06
    assert pe.build_trade_plan(_event(signal_quality_grade="A")).timeout_ms == 12000
    b = pe.build_trade_plan(_event(signal_quality_grade="B"))
    assert b.status == PLANNED and "DIAGNOSTIC" in b.reason_codes[0]
    c = pe.build_trade_plan(_event(signal_quality_grade="C"))
    assert c.status == SKIPPED
    tr = pe.build_trade_plan(_event(signal_quality_grade="TRASH"))
    assert tr.status == SKIPPED


def test_duplicate_and_non_market_skipped():
    pe = PaperEngine()
    assert pe.build_trade_plan(_event(is_duplicate_signal=True)).status == SKIPPED
    assert pe.build_trade_plan(_event(is_new_market_event=False)).status == SKIPPED
