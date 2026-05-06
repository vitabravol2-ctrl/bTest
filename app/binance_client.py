from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import json
from urllib.request import Request, urlopen

from app.binance_settings import BinanceSettings


class BinanceClient:
    def __init__(self, settings: BinanceSettings) -> None:
        self.settings = settings
        self.base_url = "https://testnet.binance.vision" if settings.use_testnet else "https://api.binance.com"

    def _http_json(self, method: str, url: str, headers: dict | None = None) -> dict:
        req = Request(url=url, method=method.upper(), headers=headers or {})
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")

    def ping(self) -> dict:
        return self._http_json("GET", f"{self.base_url}/api/v3/ping")

    def server_time(self) -> dict:
        return self._http_json("GET", f"{self.base_url}/api/v3/time")

    def _signature(self, query: str) -> str:
        return hmac.new(self.settings.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    def signed_request(self, method: str, path: str, params: dict | None = None) -> dict:
        p = dict(params or {})
        p["timestamp"] = int(time.time() * 1000)
        query = urlencode(p)
        signature = self._signature(query)
        payload = f"{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.settings.api_key}
        url = f"{self.base_url}{path}?{payload}"
        return self._http_json(method, url, headers=headers)

    def get_account(self) -> dict:
        return self.signed_request("GET", "/api/v3/account")

    def get_exchange_info(self, symbol: str) -> dict:
        return self._http_json("GET", f"{self.base_url}/api/v3/exchangeInfo?symbol={symbol}")

    def get_symbol_filters(self, symbol: str) -> list[dict]:
        info = self.get_exchange_info(symbol)
        symbols = info.get("symbols", [])
        if not symbols:
            return []
        return symbols[0].get("filters", [])

    def get_book_ticker(self, symbol: str) -> dict:
        return self._http_json("GET", f"{self.base_url}/api/v3/ticker/bookTicker?symbol={symbol}")

    def test_order_buy_market(self, symbol: str, quoteOrderQty: float) -> dict:
        return self.signed_request("POST", "/api/v3/order/test", {"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": quoteOrderQty})

    def live_order_buy_market(self, symbol: str, quoteOrderQty: float, manual_confirm: bool = False) -> dict:
        if not self.settings.live_enabled:
            return {"ok": False, "reason": "LIVE_DISABLED"}
        if self.settings.manual_confirm_required and not manual_confirm:
            return {"ok": False, "reason": "MANUAL_CONFIRM_REQUIRED"}
        return self.signed_request("POST", "/api/v3/order", {"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": quoteOrderQty})
