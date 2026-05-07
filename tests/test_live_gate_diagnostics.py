from app.live_gate import LiveGateState, recompute_live_gates


def make_state(**kw):
    base = dict(live_enabled=True,use_testnet=False,confirm_text='BUY BTCUSDT',connection_ok=True,balances_loaded=True,filters_loaded=True,order_validation_ok=True,balance_usdt=100.0,quote_amount=10.0,budget_limit=20.0,max_single_buy_usdt=20.0,has_open_position=False,sell_qty=0.0)
    base.update(kw)
    return LiveGateState(**base)


def test_buy_blocked_cases():
    assert 'LIVE_DISABLED' in recompute_live_gates(make_state(live_enabled=False)).buy_reasons
    assert 'TESTNET_ON' in recompute_live_gates(make_state(use_testnet=True)).buy_reasons
    assert 'BUY_CONFIRM_REQUIRED' in recompute_live_gates(make_state(confirm_text='x')).buy_reasons
    assert 'BALANCES_NOT_LOADED' in recompute_live_gates(make_state(balances_loaded=False)).buy_reasons
    assert 'FILTERS_NOT_LOADED' in recompute_live_gates(make_state(filters_loaded=False)).buy_reasons
    assert 'VALIDATION_NOT_OK' in recompute_live_gates(make_state(order_validation_ok=False)).buy_reasons
    assert 'QUOTE_ABOVE_BUDGET' in recompute_live_gates(make_state(quote_amount=30,budget_limit=20)).buy_reasons
    assert 'QUOTE_ABOVE_MAX_SINGLE_BUY' in recompute_live_gates(make_state(quote_amount=30,max_single_buy_usdt=20)).buy_reasons
    assert 'OPEN_POSITION_EXISTS' in recompute_live_gates(make_state(has_open_position=True)).buy_reasons


def test_buy_ready_when_all_pass():
    assert recompute_live_gates(make_state()).buy_enabled is True
