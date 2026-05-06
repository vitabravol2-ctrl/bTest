from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_PATH = Path("data/settings/binance_settings.json")


@dataclass
class BinanceSettings:
    api_key: str = ""
    api_secret: str = ""
    use_testnet: bool = False
    symbol: str = "BTCUSDT"
    quote_budget_usdt: float = 25.0
    min_trade_usdt: float = 10.0
    max_single_buy_usdt: float = 20.0
    live_enabled: bool = False
    manual_confirm_required: bool = True
    auto_exit_enabled: bool = False
    tp_pct: float = 0.05
    sl_pct: float = -0.03

    def masked_api_key(self) -> str:
        if not self.api_key:
            return ""
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return f"{self.api_key[:4]}***{self.api_key[-4:]}"

    def __repr__(self) -> str:
        return (
            "BinanceSettings(api_key='***', api_secret='***', "
            f"use_testnet={self.use_testnet}, symbol='{self.symbol}', "
            f"quote_budget_usdt={self.quote_budget_usdt}, min_trade_usdt={self.min_trade_usdt}, "
            f"max_single_buy_usdt={self.max_single_buy_usdt}, live_enabled={self.live_enabled}, "
            f"manual_confirm_required={self.manual_confirm_required}, auto_exit_enabled={self.auto_exit_enabled}, "
            f"tp_pct={self.tp_pct}, sl_pct={self.sl_pct})"
        )


def load_settings(path: Path = SETTINGS_PATH) -> BinanceSettings:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return BinanceSettings()
        return BinanceSettings(
            api_key=str(raw.get("api_key", "")),
            api_secret=str(raw.get("api_secret", "")),
            use_testnet=bool(raw.get("use_testnet", False)),
            symbol=str(raw.get("symbol", "BTCUSDT")),
            quote_budget_usdt=float(raw.get("quote_budget_usdt", 25.0)),
            min_trade_usdt=float(raw.get("min_trade_usdt", 10.0)),
            max_single_buy_usdt=float(raw.get("max_single_buy_usdt", 20.0)),
            live_enabled=bool(raw.get("live_enabled", False)),
            manual_confirm_required=bool(raw.get("manual_confirm_required", True)),
            auto_exit_enabled=bool(raw.get("auto_exit_enabled", False)),
            tp_pct=float(raw.get("tp_pct", 0.05)),
            sl_pct=float(raw.get("sl_pct", -0.03)),
        )
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return BinanceSettings()


def save_settings(settings: BinanceSettings, path: Path = SETTINGS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
