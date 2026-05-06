from app.exit_watcher import ExitWatcher
from app.position_state import PositionState


def test_watcher_updates_and_tp_trigger():
    updates = []
    triggers = []
    prices = iter([101.0, 102.0])
    pos = PositionState(symbol="BTCUSDT", entry_price=100.0, qty=1.0, tp_price=101.5, sl_price=95.0)

    w = ExitWatcher(lambda _s: next(prices, 102.0), lambda p: updates.append(p.unrealized_pnl_usdt), lambda r, _p: triggers.append(r), interval_sec=0.01)
    w.start(pos)
    import time; time.sleep(0.05)
    w.stop()
    assert updates
    assert "TP_TRIGGER" in triggers
