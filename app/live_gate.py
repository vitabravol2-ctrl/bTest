from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LiveGateState:
    live_enabled: bool
    use_testnet: bool
    confirm_text: str
    connection_ok: bool
    balances_loaded: bool
    filters_loaded: bool
    order_validation_ok: bool
    balance_usdt: float
    quote_amount: float
    budget_limit: float
    max_single_buy_usdt: float
    has_open_position: bool
    sell_qty: float


@dataclass
class GateResult:
    buy_enabled: bool
    sell_enabled: bool
    buy_reasons: list[str] = field(default_factory=list)
    sell_reasons: list[str] = field(default_factory=list)


def recompute_live_gates(state: LiveGateState, symbol: str = "BTCUSDT") -> GateResult:
    buy_reasons: list[str] = []
    sell_reasons: list[str] = []
    confirm = state.confirm_text.strip().upper()

    if not state.live_enabled:
        buy_reasons.append("LIVE_DISABLED")
    if state.use_testnet:
        buy_reasons.append("TESTNET_ON")
    if confirm != f"BUY {symbol}":
        buy_reasons.append("BUY_CONFIRM_REQUIRED")
    if not state.connection_ok:
        buy_reasons.append("CONNECTION_NOT_OK")
    if not state.balances_loaded:
        buy_reasons.append("BALANCES_NOT_LOADED")
    if not state.filters_loaded:
        buy_reasons.append("FILTERS_NOT_LOADED")
    if not state.order_validation_ok:
        buy_reasons.append("VALIDATION_NOT_OK")
    if state.balance_usdt < state.quote_amount:
        buy_reasons.append("INSUFFICIENT_USDT")
    if state.quote_amount > state.budget_limit:
        buy_reasons.append("QUOTE_ABOVE_BUDGET")
    if state.quote_amount > state.max_single_buy_usdt:
        buy_reasons.append("QUOTE_ABOVE_MAX_SINGLE_BUY")
    if state.has_open_position:
        buy_reasons.append("OPEN_POSITION_EXISTS")

    if not state.has_open_position:
        sell_reasons.append("NO_OPEN_POSITION")
    if not state.live_enabled:
        sell_reasons.append("LIVE_DISABLED")
    if confirm != f"SELL {symbol}":
        sell_reasons.append("SELL_CONFIRM_REQUIRED")
    if state.sell_qty <= 0:
        sell_reasons.append("QTY_NON_POSITIVE")

    return GateResult(
        buy_enabled=len(buy_reasons) == 0,
        sell_enabled=len(sell_reasons) == 0,
        buy_reasons=buy_reasons,
        sell_reasons=sell_reasons,
    )
