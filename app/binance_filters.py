from __future__ import annotations


def get_filter(symbol_filters: list[dict], filter_type: str) -> dict:
    for f in symbol_filters:
        if f.get("filterType") == filter_type:
            return f
    return {}


def _to_float(v: object, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def validate_market_buy_quote(symbol_filters: list[dict], quote_amount_usdt: float, ask_price: float = 0.0) -> dict:
    reasons: list[str] = []
    lot = get_filter(symbol_filters, "LOT_SIZE")
    notional = get_filter(symbol_filters, "NOTIONAL") or get_filter(symbol_filters, "MIN_NOTIONAL")

    min_qty = _to_float(lot.get("minQty", 0.0))
    step_size = _to_float(lot.get("stepSize", 0.0))
    min_notional = _to_float(notional.get("minNotional", 0.0) or notional.get("notional", 0.0))

    normalized = float(quote_amount_usdt)
    est_price = float(ask_price) if ask_price and ask_price > 0 else 0.0
    est_qty = (normalized / est_price) if est_price > 0 else 0.0

    if normalized <= 0:
        reasons.append("QUOTE_NON_POSITIVE")
    if min_notional > 0 and normalized < min_notional:
        reasons.append("MIN_NOTIONAL_FAIL")
    if est_price > 0 and min_qty > 0 and est_qty < min_qty:
        reasons.append("MIN_QTY_FAIL")
    if est_price > 0 and step_size > 0 and est_qty > 0:
        steps = round(est_qty / step_size)
        if abs(est_qty - (steps * step_size)) > (step_size * 1e-6):
            reasons.append("STEP_SIZE_FAIL")

    return {
        "ok": len(reasons) == 0,
        "normalized_quote_amount": round(normalized, 8),
        "estimated_price": est_price,
        "estimated_qty": est_qty,
        "min_notional": min_notional,
        "min_qty": min_qty,
        "step_size": step_size,
        "reason_codes": reasons,
    }
