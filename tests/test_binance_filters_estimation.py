from app.binance_filters import validate_market_buy_quote


def test_estimation_and_rules():
    filters=[{"filterType":"MIN_NOTIONAL","minNotional":"10"},{"filterType":"LOT_SIZE","minQty":"0.001","stepSize":"0.001"}]
    out = validate_market_buy_quote(filters, 20, ask_price=20000)
    assert abs(out['estimated_qty'] - 0.001) < 1e-9
    bad_qty = validate_market_buy_quote(filters, 10, ask_price=20000)
    assert 'MIN_QTY_FAIL' in bad_qty['reason_codes']
    bad_notional = validate_market_buy_quote(filters, 5, ask_price=1000)
    assert 'MIN_NOTIONAL_FAIL' in bad_notional['reason_codes']
