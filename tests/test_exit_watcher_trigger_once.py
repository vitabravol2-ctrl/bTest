import time
from app.exit_watcher import ExitWatcher
from app.position_state import PositionState


def test_tp_trigger_once_auto_exit_off():
    triggers=[]
    pos=PositionState(symbol='BTCUSDT', entry_price=100, qty=1, tp_price=101, sl_price=90, auto_exit_enabled=False)
    w=ExitWatcher(lambda _s: 102, lambda _p: None, lambda r,_p: triggers.append(r), interval_sec=0.01)
    w.start(pos); time.sleep(0.05); w.stop()
    assert triggers.count('TP_TRIGGER') == 1


def test_sl_trigger_once_auto_exit_on_callback_once():
    calls=[]
    pos=PositionState(symbol='BTCUSDT', entry_price=100, qty=1, tp_price=120, sl_price=99, auto_exit_enabled=True)
    w=ExitWatcher(lambda _s: 98, lambda _p: None, lambda r,_p: calls.append(r), interval_sec=0.01)
    w.start(pos); time.sleep(0.05); w.stop()
    assert calls == ['SL_TRIGGER']
