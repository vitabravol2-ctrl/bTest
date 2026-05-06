from __future__ import annotations


def get_filter(symbol_filters: list[dict], filter_type: str) -> dict:
    for f in symbol_filters:
        if f.get("filterType") == filter_type:
            return f
    return {}


def validate_market_buy_quote(symbol_filters: list[dict], quote_amount_usdt: float) -> dict:
    reasons: list[str] = []
    lot = get_filter(symbol_filters, "LOT_SIZE")
    notional = get_filter(symbol_filters, "NOTIONAL") or get_filter(symbol_filters, "MIN_NOTIONAL")
    _price = get_filter(symbol_filters, "PRICE_FILTER")

    min_qty = float(lot.get("minQty", 0.0))
    step_size = float(lot.get("stepSize", 0.0))
    min_notional = float(notional.get("minNotional", 0.0) or notional.get("notional", 0.0))

    normalized = float(quote_amount_usdt)
    if normalized <= 0:
        reasons.append("QUOTE_NON_POSITIVE")
    if min_notional > 0 and normalized < min_notional:
        reasons.append("MIN_NOTIONAL_FAIL")
    if min_qty > 0 and step_size > 0 and normalized < min_qty:
        reasons.append("MIN_QTY_PROXY_FAIL")

    return {"ok": len(reasons) == 0, "normalized_quote_amount": round(normalized, 8), "reason_codes": reasons}
