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
    assert s.auto_exit_enabled is False
    assert s.use_testnet is False


def test_new_risk_fields_persist(tmp_path):
    p = tmp_path / "binance_settings.json"
    s = BinanceSettings(max_single_buy_usdt=15.0, tp_pct=0.05, sl_pct=-0.03, auto_exit_enabled=False)
    save_settings(s, p)
    out = load_settings(p)
    assert out.max_single_buy_usdt == 15.0
    assert out.tp_pct == 0.05
    assert out.sl_pct == -0.03
