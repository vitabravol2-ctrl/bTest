from app.order_preview import OrderPreview


def test_order_preview_defaults():
    p = OrderPreview(symbol="BTCUSDT")
    assert p.side == "BUY"
    assert p.can_submit_live_order is False
