from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

POSITION_PATH = Path("data/runtime/open_position.json")


@dataclass
class PositionState:
    symbol: str
    side: str = "LONG"
    status: str = "OPEN"
    entry_price: float = 0.0
    qty: float = 0.0
    spent_usdt: float = 0.0
    fee_usdt: float = 0.0
    entry_ts_ms: int = 0
    tp_pct: float = 0.0
    sl_pct: float = 0.0
    tp_price: float = 0.0
    sl_price: float = 0.0
    auto_exit_enabled: bool = False
    realized_pnl_usdt: float = 0.0
    realized_pnl_pct: float = 0.0
    last_price: float = 0.0
    unrealized_pnl_usdt: float = 0.0
    unrealized_pnl_pct: float = 0.0
    exit_reason: str = ""
    closed_ts_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "PositionState":
        defaults = cls(symbol=str(raw.get("symbol", "BTCUSDT")))
        payload = {}
        for field in cls.__dataclass_fields__:
            payload[field] = raw.get(field, getattr(defaults, field))
        return cls(**payload)


def save_position(position: PositionState, path: Path = POSITION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(position.to_dict(), indent=2), encoding="utf-8")


def load_position(path: Path = POSITION_PATH) -> PositionState | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        pos = PositionState.from_dict(raw)
        return pos if pos.status == "OPEN" else None
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return None


def clear_position(path: Path = POSITION_PATH) -> None:
    if path.exists():
        path.unlink()
