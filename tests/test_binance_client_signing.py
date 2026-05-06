from app.binance_client import BinanceClient
from app.binance_settings import BinanceSettings


def test_signature_deterministic():
    c = BinanceClient(BinanceSettings(api_secret="x"))
    s1 = c._signature("a=1&b=2")
    s2 = c._signature("a=1&b=2")
    assert s1 == s2


def test_live_order_blocked_by_default():
    c = BinanceClient(BinanceSettings(live_enabled=False, manual_confirm_required=True))
    out = c.live_order_buy_market("BTCUSDT", 20, manual_confirm=True)
    assert out["reason"] == "LIVE_DISABLED"


def test_manual_confirm_required():
    c = BinanceClient(BinanceSettings(live_enabled=True, manual_confirm_required=True))
    out = c.live_order_buy_market("BTCUSDT", 20, manual_confirm=False)
    assert out["reason"] == "MANUAL_CONFIRM_REQUIRED"
