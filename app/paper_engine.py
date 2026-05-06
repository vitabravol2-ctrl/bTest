from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.trade_plan import INVALID, PLANNED, SKIPPED, TradePlan


@dataclass(frozen=True)
class PaperEngineConfig:
    a_plus_tp_pct: float = 0.06
    a_plus_sl_pct: float = 0.03
    a_plus_timeout_ms: int = 15000
    a_tp_pct: float = 0.05
    a_sl_pct: float = 0.03
    a_timeout_ms: int = 12000
    b_tp_pct: float = 0.03
    b_sl_pct: float = 0.02
    b_timeout_ms: int = 10000


class PaperEngine:
    def __init__(self, config: PaperEngineConfig | None = None) -> None:
        self.config = config or PaperEngineConfig()
        self._plan_seq = 0

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def build_trade_plan(self, signal_event: dict[str, Any]) -> TradePlan:
        self._plan_seq += 1
        is_market = bool(signal_event.get("is_new_market_event", False))
        is_duplicate = bool(signal_event.get("is_duplicate_signal", False))
        detected = bool(signal_event.get("detected", False))
        grade = str(signal_event.get("signal_quality_grade", signal_event.get("signal_grade", ""))).upper()

        cluster_id = self._to_int(signal_event.get("signal_cluster_id", 0))
        symbol = str(signal_event.get("symbol", ""))
        side = str(signal_event.get("side", "LONG"))
        score = self._to_float(signal_event.get("signal_quality_score", 0.0))
        price = self._to_float(signal_event.get("trigger_price", signal_event.get("last_price", signal_event.get("price", 0.0))))
        ts_ms = self._to_int(signal_event.get("ts_ms", signal_event.get("ts", 0)))

        if not is_market:
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", 0.0, 0.0, 0.0, 0, SKIPPED, ["NON_MARKET_EVENT"])
        if is_duplicate:
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", 0.0, 0.0, 0.0, 0, SKIPPED, ["DUPLICATE_SIGNAL"])
        if not detected:
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", 0.0, 0.0, 0.0, 0, INVALID, ["NOT_DETECTED"])

        if grade == "A_PLUS":
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", price, self.config.a_plus_tp_pct, self.config.a_plus_sl_pct, self.config.a_plus_timeout_ms, PLANNED, ["GRADE_A_PLUS"])
        if grade == "A":
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", price, self.config.a_tp_pct, self.config.a_sl_pct, self.config.a_timeout_ms, PLANNED, ["GRADE_A"])
        if grade == "B":
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", price, self.config.b_tp_pct, self.config.b_sl_pct, self.config.b_timeout_ms, PLANNED, ["GRADE_B_DIAGNOSTIC"])
        if grade in {"C", "TRASH"}:
            return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", 0.0, 0.0, 0.0, 0, SKIPPED, [f"GRADE_{grade}"])
        return TradePlan(self._plan_seq, cluster_id, symbol, side, grade, score, price, ts_ms, "MARKET", 0.0, 0.0, 0.0, 0, INVALID, ["UNKNOWN_GRADE"])
