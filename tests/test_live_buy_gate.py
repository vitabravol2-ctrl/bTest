from app.binance_client import BinanceClient
from app.binance_settings import BinanceSettings


def test_live_disabled_blocks_buy():
    c = BinanceClient(BinanceSettings(live_enabled=False))
    r = c.live_order_buy_market("BTCUSDT", 10.0, manual_confirm=True)
    assert r["reason"] == "LIVE_DISABLED"
