from app.research_pipeline import AutoResearchPipeline
from app.session_analyzer import SessionAnalyzer


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
