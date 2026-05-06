from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PaperTrade:
    entry_ts: int
    entry_price: float
    exit_ts: int = 0
    exit_price: float = 0.0
    pnl_pct: float = 0.0
    result: str = "OPEN"
    max_favorable_move_pct: float = 0.0
    max_adverse_move_pct: float = 0.0
    gross_pnl_usdt: float = 0.0
    net_pnl_usdt: float = 0.0
    net_pnl_pct_on_trade: float = 0.0
    fees_usdt: float = 0.0


class PaperSimulator:
    def __init__(self, take_profit_pct: float = 0.03, stop_loss_pct: float = 0.02, max_hold_seconds: int = 30, starting_balance_usdt: float = 1000.0, trade_size_usdt: float = 100.0, fee_rate_pct: float = 0.075, bnb_fee_discount_enabled: bool = True, bnb_discount_factor: float = 0.75) -> None:
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_seconds = max_hold_seconds
        self.enabled = True
        self.starting_balance_usdt = starting_balance_usdt
        self.trade_size_usdt = trade_size_usdt
        self.fee_rate_pct = fee_rate_pct
        self.bnb_fee_discount_enabled = bnb_fee_discount_enabled
        self.bnb_discount_factor = bnb_discount_factor
        self.open_trade: PaperTrade | None = None
        self.trades: list[PaperTrade] = []
    @property
    def effective_fee_pct(self) -> float:
        return self.fee_rate_pct * self.bnb_discount_factor if self.bnb_fee_discount_enabled else self.fee_rate_pct

    def open_long(self, ts_ms: int, entry_price: float) -> bool:
        if (not self.enabled) or self.open_trade is not None or entry_price <= 0:
            return False
        self.open_trade = PaperTrade(entry_ts=ts_ms, entry_price=entry_price)
        return True

    def on_tick(self, ts_ms: int, bid: float, ask: float) -> PaperTrade | None:
        trade = self.open_trade
        if (not self.enabled) or trade is None:
            return None
        price = ask if ask > 0 else bid
        if price <= 0:
            return None
        move_pct = ((price - trade.entry_price) / trade.entry_price)
        trade.max_favorable_move_pct = max(trade.max_favorable_move_pct, move_pct)
        trade.max_adverse_move_pct = min(trade.max_adverse_move_pct, move_pct)
        if move_pct >= self.take_profit_pct:
            return self._close(ts_ms, price, "WIN")
        if move_pct <= -self.stop_loss_pct:
            return self._close(ts_ms, price, "LOSS")
        if (ts_ms - trade.entry_ts) >= self.max_hold_seconds * 1000:
            return self._close(ts_ms, price, "TIMEOUT")
        return None

    def _close(self, ts_ms: int, price: float, result: str) -> PaperTrade:
        trade = self.open_trade
        assert trade is not None
        trade.exit_ts = ts_ms
        trade.exit_price = price
        qty = self.trade_size_usdt / trade.entry_price
        exit_value = qty * price
        gross_pnl = qty * (price - trade.entry_price)
        entry_fee = self.trade_size_usdt * self.effective_fee_pct / 100.0
        exit_fee = exit_value * self.effective_fee_pct / 100.0
        net_pnl = gross_pnl - entry_fee - exit_fee
        trade.pnl_pct = ((price - trade.entry_price) / trade.entry_price) * 100.0
        trade.gross_pnl_usdt = gross_pnl
        trade.net_pnl_usdt = net_pnl
        trade.net_pnl_pct_on_trade = (net_pnl / self.trade_size_usdt) * 100.0
        trade.fees_usdt = entry_fee + exit_fee
        trade.result = result
        trade.max_favorable_move_pct *= 100.0
        trade.max_adverse_move_pct *= 100.0
        self.trades.append(trade)
        self.open_trade = None
        return trade

    def stats(self) -> dict[str, float | str | int]:
        wins = sum(1 for t in self.trades if t.result == "WIN")
        losses = sum(1 for t in self.trades if t.result == "LOSS")
        timeouts = sum(1 for t in self.trades if t.result == "TIMEOUT")
        n = len(self.trades)
        total_pnl = sum(t.pnl_pct for t in self.trades)
        gross_pnl_usdt = sum(t.gross_pnl_usdt for t in self.trades)
        net_pnl_usdt = sum(t.net_pnl_usdt for t in self.trades)
        equity = self.starting_balance_usdt + net_pnl_usdt
        return {
            "paper_mode": "ON" if self.enabled else "OFF",
            "starting_balance_usdt": self.starting_balance_usdt,
            "trade_size_usdt": self.trade_size_usdt,
            "fee_effective_pct": self.effective_fee_pct,
            "open_trade": "YES" if self.open_trade else "NO",
            "paper_trades": n,
            "wins": wins,
            "losses": losses,
            "timeouts": timeouts,
            "winrate": (wins / n * 100.0) if n else 0.0,
            "avg_pnl": (total_pnl / n) if n else 0.0,
            "total_pnl": total_pnl,
            "gross_pnl_usdt": gross_pnl_usdt,
            "net_pnl_usdt": net_pnl_usdt,
            "net_pnl_pct": (net_pnl_usdt / self.starting_balance_usdt * 100.0) if self.starting_balance_usdt else 0.0,
            "equity_usdt": equity,
            "last_trade_result": self.trades[-1].result if self.trades else "-",
            "max_favorable_avg": (sum(t.max_favorable_move_pct for t in self.trades) / n) if n else 0.0,
            "max_adverse_avg": (sum(t.max_adverse_move_pct for t in self.trades) / n) if n else 0.0,
        }
