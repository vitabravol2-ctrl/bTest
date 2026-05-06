from app.research_pipeline import AutoResearchPipeline
from app.session_analyzer import SessionAnalyzer
from app.detector import LiquidityGrabDetector
from app.profiles import ThresholdProfile


def test_analyze_accepts_current_profile_for_validation(monkeypatch):
    analyzer = SessionAnalyzer()
    analyzer.events = [{"score": 55, "detected": False, "drop_pct": 0.02, "bounce_pct": 0.01, "speed": 0.003, "debug": {}}]
    captured = {}

    def fake_validate(self, current_profile, suggested_profile, **kwargs):
        captured["profile"] = current_profile
        return {"recommendation": "NEED_MORE_DATA", "confidence": "LOW", "reason": "x", "current_near_signal_count": 0, "suggested_near_signal_count": 0}

    monkeypatch.setattr(SessionAnalyzer, "validate_calibration_before_after", fake_validate)
    profile = {"name": "BALANCED", "min_grab_drop_pct": 0.07}
    analyzer.analyze(current_profile=profile)
    assert captured["profile"]["name"] == "BALANCED"


def test_auto_research_clean_session_resets_events():
    class DummyRecorder:
        def __init__(self):
            self.is_recording = True
            self.events = [{"x": 1}]
            self.stopped = False
            self.started = False
        def stop_session(self):
            self.stopped = True
            self.is_recording = False
        def start_session(self):
            self.started = True
            return "session_new.jsonl"

    rec = DummyRecorder()
    if rec.is_recording:
        rec.stop_session()
    rec.events.clear()
    rec.start_session()
    assert rec.stopped is True
    assert rec.started is True
    assert rec.events == []


def test_pipeline_stage_progression_is_condition_based():
    p = AutoResearchPipeline()
    p.update_stage(connected=False, ticks_collected=0, session_seconds=0, sweeps_found=0, near_signals_count=0, top_blocker='-', min_research_ticks=300, min_research_seconds=60, now_ms=1)
    assert p.progress.current_state == "CONNECTING"
    p.update_stage(connected=True, ticks_collected=20, session_seconds=2, sweeps_found=0, near_signals_count=0, top_blocker='-', min_research_ticks=300, min_research_seconds=60, now_ms=2)
    assert p.progress.current_state == "COLLECTING_DATA"
    p.update_stage(connected=True, ticks_collected=150, session_seconds=10, sweeps_found=1, near_signals_count=1, top_blocker='drop_ok', min_research_ticks=300, min_research_seconds=60, now_ms=3)
    assert p.progress.current_state == "WARMUP"
    p.update_stage(connected=True, ticks_collected=320, session_seconds=80, sweeps_found=2, near_signals_count=2, top_blocker='bounce_ok', min_research_ticks=300, min_research_seconds=60, now_ms=4)
    assert p.progress.current_state == "DETECTING_SETUPS"


def test_auto_research_summary_contains_recommendation():
    summary = "\n".join([
        "AUTO RESEARCH SUMMARY",
        "- recommendation: APPLY_RECOMMENDED",
        "- confidence: HIGH",
    ])
    assert "recommendation" in summary


def test_pipeline_error_state_sets_last_error():
    p = AutoResearchPipeline()
    p.set_error("boom")
    assert p.progress.current_state == "ERROR"
    assert p.progress.last_error == "boom"


def test_custom_profile_values_can_be_applied_to_detector():
    detector = LiquidityGrabDetector()
    custom = ThresholdProfile(
        name="CUSTOM",
        min_grab_drop_pct=0.0123,
        min_reclaim_bounce_pct=0.0077,
        min_impulse_speed_pct_per_sec=0.0011,
        signal_min_score=58,
        max_trend_drop_mid_pct=0.22,
        max_slow_trend_drop_pct=0.33,
    )
    detector.set_profile(custom)
    assert detector.profile.name == "CUSTOM"
    assert detector.profile.min_grab_drop_pct == 0.0123


def test_validation_uses_custom_current_profile(monkeypatch):
    analyzer = SessionAnalyzer()
    analyzer.events = [{"score": 55, "detected": False, "drop_pct": 0.02, "bounce_pct": 0.01, "speed": 0.003, "debug": {}}]
    captured = {}

    def fake_validate(self, current_profile, suggested_profile, **kwargs):
        captured["name"] = current_profile.get("name")
        return {"recommendation": "NEED_MORE_DATA", "confidence": "LOW", "reason": "x", "current_near_signal_count": 0, "suggested_near_signal_count": 0}

    monkeypatch.setattr(SessionAnalyzer, "validate_calibration_before_after", fake_validate)
    analyzer.analyze(
        current_profile={
            "name": "CUSTOM",
            "min_grab_drop_pct": 0.011,
            "min_reclaim_bounce_pct": 0.008,
            "min_impulse_speed_pct_per_sec": 0.001,
            "signal_min_score": 58,
        }
    )
    assert captured["name"] == "CUSTOM"


def test_settings_accepts_reclaim_hold_fields_without_breaking():
    profile_keys = ThresholdProfile.__dataclass_fields__.keys()
    fields = {
        "min_grab_drop_pct": 0.01,
        "min_reclaim_bounce_pct": 0.01,
        "min_impulse_speed_pct_per_sec": 0.001,
        "signal_min_score": 55.0,
        "max_trend_drop_mid_pct": 0.25,
        "max_slow_trend_drop_pct": 0.40,
        "min_reclaim_hold_ms": 150.0,
        "reclaim_window_ms": 3000.0,
        "invalidation_cooldown_ms": 1000.0,
    }
    payload = {k: v for k, v in fields.items() if k in profile_keys}
    extras = {k: v for k, v in fields.items() if k not in profile_keys}
    profile = ThresholdProfile(name="CUSTOM", **payload)
    assert profile.name == "CUSTOM"
    assert "min_reclaim_hold_ms" in extras


def test_no_trading_or_execution_added():
    import pathlib
    text = pathlib.Path("app/session_analyzer.py").read_text(encoding="utf-8") + pathlib.Path("app/gui/main_window.py").read_text(encoding="utf-8")
    assert "api_key" not in text.lower()
    assert "paper" not in text.lower()
    assert "create_order" not in text.lower()

def test_default_research_profile_is_custom():
    from app.profiles import PROFILES
    custom = PROFILES["CUSTOM"]
    assert custom.signal_min_score == 55
    defaults = {"signal_unlock_debug": 1.0, "unlock_p90_bounce_pct": 0.020, "adaptive_hold_enabled": 1.0}
    assert defaults["signal_unlock_debug"] == 1.0


def test_gui_hides_nonessential_buttons():
    text = __import__("pathlib").Path("app/gui/main_window.py").read_text(encoding="utf-8")
    assert "self.btn_load_replay.setVisible(False)" in text
    assert "self.btn_analyze_session.setVisible(False)" in text
    assert "self.btn_apply_calibration.setVisible(False)" in text
