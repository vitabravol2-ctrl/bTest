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


class PaperSimulator:
    def __init__(self, take_profit_pct: float = 0.03, stop_loss_pct: float = 0.02, max_hold_seconds: int = 30) -> None:
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_hold_seconds = max_hold_seconds
        self.enabled = True
        self.open_trade: PaperTrade | None = None
        self.trades: list[PaperTrade] = []

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
        trade.pnl_pct = ((price - trade.entry_price) / trade.entry_price) * 100.0
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
        return {
            "paper_trades": n,
            "wins": wins,
            "losses": losses,
            "timeouts": timeouts,
            "winrate": (wins / n * 100.0) if n else 0.0,
            "avg_pnl": (total_pnl / n) if n else 0.0,
            "total_pnl": total_pnl,
            "last_trade_result": self.trades[-1].result if self.trades else "-",
            "max_favorable_avg": (sum(t.max_favorable_move_pct for t in self.trades) / n) if n else 0.0,
            "max_adverse_avg": (sum(t.max_adverse_move_pct for t in self.trades) / n) if n else 0.0,
        }
