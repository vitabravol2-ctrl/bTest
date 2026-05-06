from app.binance_settings import BinanceSettings, load_settings, save_settings


def test_settings_save_load(tmp_path):
    p = tmp_path / "binance_settings.json"
    s = BinanceSettings(api_key="abc12345", api_secret="sec", quote_budget_usdt=30)
    save_settings(s, p)
    out = load_settings(p)
    assert out.api_key == "abc12345"
    assert out.api_secret == "sec"


def test_repr_masks_secrets():
    s = BinanceSettings(api_key="abcd1234", api_secret="SECRET")
    r = repr(s)
    assert "SECRET" not in r


def test_empty_settings_safe(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    s = load_settings(p)
    assert s.symbol == "BTCUSDT"
