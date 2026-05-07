from app.live_gate import LiveGateState, recompute_live_gates


def base(**kw):
    d = dict(live_enabled=True,use_testnet=False,confirm_text='SELL BTCUSDT',connection_ok=True,balances_loaded=True,filters_loaded=True,order_validation_ok=True,balance_usdt=100.0,quote_amount=10.0,budget_limit=20.0,max_single_buy_usdt=20.0,has_open_position=True,sell_qty=0.1)
    d.update(kw)
    return LiveGateState(**d)


def test_sell_blocks_and_ready():
    assert 'NO_OPEN_POSITION' in recompute_live_gates(base(has_open_position=False)).sell_reasons
    assert 'SELL_CONFIRM_REQUIRED' in recompute_live_gates(base(confirm_text='x')).sell_reasons
    assert 'LIVE_DISABLED' in recompute_live_gates(base(live_enabled=False)).sell_reasons
    assert recompute_live_gates(base()).sell_enabled is True
