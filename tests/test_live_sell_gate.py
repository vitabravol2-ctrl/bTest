from app.binance_client import BinanceClient
from app.binance_settings import BinanceSettings


def test_sell_blocked_without_confirm():
    c = BinanceClient(BinanceSettings(live_enabled=True, manual_confirm_required=True))
    r = c.live_order_sell_market("BTCUSDT", 0.001, manual_confirm=False)
    assert r["reason"] == "MANUAL_CONFIRM_REQUIRED"


def test_live_disabled_blocks_sell():
    c = BinanceClient(BinanceSettings(live_enabled=False))
    r = c.live_order_sell_market("BTCUSDT", 0.001, manual_confirm=True)
    assert r["reason"] == "LIVE_DISABLED"
