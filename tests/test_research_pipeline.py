from app.research_pipeline import AutoResearchPipeline


def test_research_pipeline_initial_state():
    pipeline = AutoResearchPipeline()
    progress = pipeline.progress
    assert progress.current_state == "IDLE"
    assert progress.progress_pct == 0
    assert progress.suggested_action == "NONE"


def test_research_pipeline_progress_fields():
    pipeline = AutoResearchPipeline()
    pipeline.start()
    pipeline.set_warmup(120, 30)
    pipeline.set_detecting(4, 2, "bounce_ok")
    pipeline.set_decision("APPLY_RECOMMENDED", "HIGH", "improved")
    progress = pipeline.progress
    assert progress.current_state == "DECISION"
    assert progress.ticks_collected == 120
    assert progress.sweeps_found == 4
    assert progress.near_signals_count == 2
    assert progress.top_blocker == "bounce_ok"
    assert progress.suggested_action == "APPLY_RECOMMENDED"
