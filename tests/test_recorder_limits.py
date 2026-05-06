import json

from app.config import MAX_GUI_LOG_LINES
from app.recorder import SignalRecorder


class Dummy:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_recorder_keeps_memory_limited_but_file_full(tmp_path):
    recorder = SignalRecorder(data_dir=tmp_path, max_buffer=2)
    recorder.MAX_IN_MEMORY_EVENTS = 5
    recorder.start_session()
    for i in range(12):
        tick = Dummy(ts_ms=i, mid=100.0, bid=99.9, ask=100.1)
        metrics = Dummy(drop_pct=0.01, bounce_pct=0.01, impulse_speed_pct_per_sec=0.001, volatility_pct=0.001, spread_avg_pct=0.001)
        signal = Dummy(phase="NO_SETUP", score=1.0, detected=False, reason_codes=[], debug={})
        profile = Dummy(name="TEST", min_grab_drop_pct=0.01, min_reclaim_bounce_pct=0.01, signal_min_score=50)
        recorder.record_tick(tick, metrics, signal, "S", profile)
    recorder.stop_session()
    assert len(recorder.events) == 5
    with recorder.session_path.open("r", encoding="utf-8") as f:  # type: ignore[union-attr]
        lines = [json.loads(x) for x in f if x.strip()]
    assert len(lines) == 12


def test_gui_log_limit_constant_exists():
    assert MAX_GUI_LOG_LINES == 1000

def test_recorder_saves_would_signal_fields(tmp_path):
    recorder = SignalRecorder(data_dir=tmp_path, max_buffer=1)
    recorder.start_session()
    tick = Dummy(ts_ms=1, mid=100.0, bid=99.9, ask=100.1)
    metrics = Dummy(drop_pct=0.2, bounce_pct=0.01, impulse_speed_pct_per_sec=0.01, volatility_pct=0.001, spread_avg_pct=0.001)
    signal = Dummy(phase="RECLAIM_WAIT", score=80.0, detected=False, reason_codes=["SWEEP_FOUND"], debug={}, would_signal=True, would_signal_reason="WOULD_SIGNAL_BOUNCE", unlock_debug_active=True, unlock_blocker="bounce_ok", unlock_reason="WOULD_SIGNAL_BOUNCE")
    profile = Dummy(name="TEST", min_grab_drop_pct=0.01, min_reclaim_bounce_pct=0.01, signal_min_score=50)
    recorder.record_tick(tick, metrics, signal, "S", profile)
    recorder.stop_session()
    row = json.loads(recorder.session_path.read_text(encoding='utf-8').strip())
    assert row["would_signal"] is True
    assert row["would_signal_reason"] == "WOULD_SIGNAL_BOUNCE"
    assert row["unlock_debug_active"] is True

def test_recorder_saves_adaptive_hold_fields(tmp_path):
    recorder = SignalRecorder(data_dir=tmp_path, max_buffer=1)
    recorder.start_session()
    tick = Dummy(ts_ms=1, mid=100.0, bid=99.9, ask=100.1)
    metrics = Dummy(drop_pct=0.2, bounce_pct=0.01, impulse_speed_pct_per_sec=0.01, volatility_pct=0.001, spread_avg_pct=0.001)
    signal = Dummy(phase="RECLAIM_WAIT", score=80.0, detected=False, reason_codes=["SWEEP_FOUND"], debug={}, adaptive_hold_active=True, base_hold_ms=1500, effective_hold_ms=500, hold_reduction_reason="score>=80")
    profile = Dummy(name="TEST", min_grab_drop_pct=0.01, min_reclaim_bounce_pct=0.01, signal_min_score=50)
    recorder.record_tick(tick, metrics, signal, "S", profile)
    recorder.stop_session()
    row = json.loads(recorder.session_path.read_text(encoding='utf-8').strip())
    assert row["adaptive_hold_active"] is True
    assert row["effective_hold_ms"] == 500


def test_recorder_saves_effective_bounce_fields(tmp_path):
    recorder = SignalRecorder(data_dir=tmp_path, max_buffer=1)
    recorder.start_session()
    tick = Dummy(ts_ms=1, mid=100.0, bid=99.9, ask=100.1)
    metrics = Dummy(drop_pct=0.2, bounce_pct=0.01, impulse_speed_pct_per_sec=0.01, volatility_pct=0.001, spread_avg_pct=0.001)
    signal = Dummy(phase="RECLAIM_WAIT", score=80.0, detected=False, reason_codes=["SWEEP_FOUND"], debug={}, effective_bounce_threshold=0.003, base_bounce_threshold=0.01, reclaim_level_source="adaptive_unlock_p90_0.75", reclaim_distance_pct=0.05)
    profile = Dummy(name="TEST", min_grab_drop_pct=0.01, min_reclaim_bounce_pct=0.01, signal_min_score=50)
    recorder.record_tick(tick, metrics, signal, "S", profile)
    recorder.stop_session()
    row = json.loads(recorder.session_path.read_text(encoding="utf-8").strip())
    assert row["effective_bounce_threshold"] == 0.003
    assert row["base_bounce_threshold"] == 0.01
    assert row["reclaim_level_source"] == "adaptive_unlock_p90_0.75"
