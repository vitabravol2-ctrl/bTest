from app.profiles import BASELINE, PROFILES, get_profile
from app.session_analyzer import SessionAnalyzer


def test_profiles_contains_only_baseline():
    assert set(PROFILES.keys()) == {"BASELINE"}


def test_legacy_profile_names_return_baseline():
    legacy = ["CONSERVATIVE", "BALANCED", "SENSITIVE", "DEBUG_ULTRA", "CUSTOM", "CUSTOM_EXTREME_RESEARCH"]
    for name in legacy:
        assert get_profile(name) == BASELINE


def test_legacy_profile_name_in_event_does_not_break_analyzer(tmp_path):
    p = tmp_path / "legacy.jsonl"
    p.write_text('{"profile_name":"CONSERVATIVE","is_new_market_event":false}\n', encoding="utf-8")
    sa = SessionAnalyzer()
    sa.load(p)
    data = sa.analyze()
    assert data["total_events"] == 1
