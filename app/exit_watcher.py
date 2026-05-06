from __future__ import annotations

import threading
import time
from collections.abc import Callable

from app.position_state import PositionState


class ExitWatcher:
    def __init__(
        self,
        get_price: Callable[[str], float],
        on_update: Callable[[PositionState], None],
        on_trigger: Callable[[str, PositionState], None],
        interval_sec: float = 0.35,
    ) -> None:
        self.get_price = get_price
        self.on_update = on_update
        self.on_trigger = on_trigger
        self.interval_sec = interval_sec
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self, position: PositionState) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(position,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self, position: PositionState) -> None:
        while not self._stop.is_set() and position.status == "OPEN":
            price = float(self.get_price(position.symbol))
            position.last_price = price
            position.unrealized_pnl_usdt = (price - position.entry_price) * position.qty
            position.unrealized_pnl_pct = ((price / position.entry_price - 1.0) * 100.0) if position.entry_price else 0.0
            self.on_update(position)
            reason = ""
            if position.tp_price and price >= position.tp_price:
                reason = "TP_TRIGGER"
            elif position.sl_price and price <= position.sl_price:
                reason = "SL_TRIGGER"
            if reason:
                self.on_trigger(reason, position)
            time.sleep(self.interval_sec)
