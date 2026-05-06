import json

from app.profiles import BASELINE, PROFILES, get_profile
from app.session_analyzer import SessionAnalyzer


def test_profiles_contains_only_baseline():
    assert list(PROFILES.keys()) == ["BASELINE"]


def test_get_profile_legacy_fallback():
    assert get_profile("CUSTOM_EXTREME_RESEARCH") == BASELINE
    assert get_profile("CUSTOM") == BASELINE


def test_legacy_profile_name_in_jsonl_does_not_break(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps({"profile_name": "CUSTOM_EXTREME_RESEARCH", "is_new_market_event": False}) + "\n", encoding="utf-8")
    analyzer = SessionAnalyzer()
    analyzer.load(path)
    data = analyzer.analyze()
    assert data["total_events"] == 1


def test_gui_settings_fallback_safe():
    assert get_profile("SENSITIVE").name == "BASELINE"
