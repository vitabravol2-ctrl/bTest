from __future__ import annotations

from dataclasses import dataclass


PLANNED = "PLANNED"
SKIPPED = "SKIPPED"
INVALID = "INVALID"


@dataclass(slots=True)
class TradePlan:
    plan_id: int
    source_signal_cluster_id: int
    symbol: str
    side: str
    signal_grade: str
    signal_quality_score: float
    reference_price: float
    created_ts_ms: int
    entry_type: str
    entry_price: float
    tp_pct: float
    sl_pct: float
    timeout_ms: int
    status: str
    reason_codes: list[str]
