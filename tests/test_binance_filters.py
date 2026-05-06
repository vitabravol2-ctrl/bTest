from app.binance_filters import validate_market_buy_quote


def test_min_notional_validation():
    filters = [{"filterType": "MIN_NOTIONAL", "minNotional": "10"}, {"filterType": "LOT_SIZE", "minQty": "0.0001", "stepSize": "0.0001"}]
    bad = validate_market_buy_quote(filters, 5)
    ok = validate_market_buy_quote(filters, 15)
    assert not bad["ok"]
    assert "MIN_NOTIONAL_FAIL" in bad["reason_codes"]
    assert ok["ok"]


def test_budget_below_min_trade_rejected():
    filters = [{"filterType": "MIN_NOTIONAL", "minNotional": "1"}]
    out = validate_market_buy_quote(filters, 0.5)
    assert out["ok"] is False
