from dataclasses import dataclass, field


@dataclass(slots=True)
class LiquidityGrabSignal:
    detected: bool = False
    side: str = "NONE"
    score: float = 0.0
    phase: str = "NO_SETUP"
    trigger_price: float | None = None
    grab_low: float | None = None
    reclaim_level: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    human_reason: str = "Waiting setup"
    ts_ms: int = 0
    setup_age_ms: int = 0
    reclaim_hold_ms: int = 0
    last_invalid_reason: str = "-"
    debug: dict[str, bool] = field(default_factory=dict)
    would_signal: bool = False
    would_signal_reason: str = ""
    unlock_debug_active: bool = False
    unlock_blocker: str = ""
    unlock_reason: str = ""
