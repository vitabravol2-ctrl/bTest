from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SignalRecorder:
    MAX_IN_MEMORY_EVENTS = 50_000

    def __init__(self, data_dir: str | Path = "data/sessions", max_buffer: int = 5000, flush_interval_sec: float = 2.0) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_buffer = max_buffer
        self.flush_interval_sec = flush_interval_sec

        self._buffer: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._active = False
        self._session_path: Path | None = None
        self._last_flush_monotonic = 0.0

    @property
    def is_recording(self) -> bool:
        return self._active

    @property
    def session_path(self) -> Path | None:
        return self._session_path

    def start_session(self) -> Path:
        if self._active:
            return self._session_path  # type: ignore[return-value]

        timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        self._session_path = self.data_dir / f"session_{timestamp}.jsonl"
        self._session_path.touch(exist_ok=True)
        self._buffer.clear()
        self.events.clear()
        self._active = True
        self._last_flush_monotonic = time.monotonic()
        return self._session_path

    def stop_session(self) -> None:
        if not self._active:
            return
        self.flush_to_file()
        self._active = False

    def record_tick(self, tick, metrics, signal, fsm_state: str, profile=None) -> None:
        if not self._active:
            return

        event = {
            "ts": int(getattr(tick, "ts_ms", int(time.time() * 1000))),
            "price": float(getattr(tick, "mid", 0.0)),
            "bid": float(getattr(tick, "bid", 0.0)),
            "ask": float(getattr(tick, "ask", 0.0)),
            "drop_pct": float(getattr(metrics, "drop_pct", 0.0)),
            "bounce_pct": float(getattr(metrics, "bounce_pct", 0.0)),
            "speed": float(getattr(metrics, "impulse_speed_pct_per_sec", 0.0)),
            "volatility": float(getattr(metrics, "volatility_pct", 0.0)),
            "spread": float(getattr(metrics, "spread_avg_pct", 0.0)),
            "phase": str(getattr(signal, "phase", "NO_SETUP")),
            "score": float(getattr(signal, "score", 0.0)),
            "signal": "LONG_SIGNAL" if bool(getattr(signal, "detected", False)) else "NO_SIGNAL",
            "fsm_state": fsm_state,
            "reason_codes": list(getattr(signal, "reason_codes", [])),
            "detected": bool(getattr(signal, "detected", False)),
            "would_signal": bool(getattr(signal, "would_signal", False)),
            "would_signal_reason": str(getattr(signal, "would_signal_reason", "")),
            "unlock_debug_active": bool(getattr(signal, "unlock_debug_active", False)),
            "unlock_blocker": str(getattr(signal, "unlock_blocker", "")),
            "unlock_reason": str(getattr(signal, "unlock_reason", "")),
            "adaptive_hold_active": bool(getattr(signal, "adaptive_hold_active", False)),
            "base_hold_ms": int(getattr(signal, "base_hold_ms", 0)),
            "effective_hold_ms": int(getattr(signal, "effective_hold_ms", 0)),
            "hold_reduction_reason": str(getattr(signal, "hold_reduction_reason", "")),
            "effective_bounce_threshold": float(getattr(signal, "effective_bounce_threshold", 0.0)),
            "base_bounce_threshold": float(getattr(signal, "base_bounce_threshold", 0.0)),
            "reclaim_level_source": str(getattr(signal, "reclaim_level_source", "")),
            "reclaim_distance_pct": float(getattr(signal, "reclaim_distance_pct", 0.0)),
            "debug": dict(getattr(signal, "debug", {})),
            "profile_name": str(getattr(profile, "name", "CONSERVATIVE")),
            "thresholds": {
                "min_grab_drop_pct": float(getattr(profile, "min_grab_drop_pct", 0.08)),
                "min_reclaim_bounce_pct": float(getattr(profile, "min_reclaim_bounce_pct", 0.04)),
                "signal_min_score": float(getattr(profile, "signal_min_score", 70.0)),
            },
        }
        self._buffer.append(event)
        self.events.append(event)
        if len(self.events) > self.MAX_IN_MEMORY_EVENTS:
            self.events = self.events[-self.MAX_IN_MEMORY_EVENTS :]

        now = time.monotonic()
        if len(self._buffer) >= self.max_buffer or now - self._last_flush_monotonic >= self.flush_interval_sec:
            self.flush_to_file()

    def flush_to_file(self) -> None:
        if not self._buffer or not self._session_path:
            return

        with self._session_path.open("a", encoding="utf-8") as f:
            for item in self._buffer:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        self._buffer.clear()
        self._last_flush_monotonic = time.monotonic()
