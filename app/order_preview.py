from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderPreview:
    symbol: str
    side: str = "BUY"
    type: str = "MARKET"
    quote_amount: float = 0.0
    estimated_price: float = 0.0
    estimated_qty: float = 0.0
    filters_ok: bool = False
    balance_ok: bool = False
    budget_ok: bool = False
    can_submit_test_order: bool = False
    can_submit_live_order: bool = False
    reason_codes: list[str] = field(default_factory=list)
