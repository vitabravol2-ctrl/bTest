from app.position_state import PositionState, clear_position, load_position, save_position


def test_position_persistence_restore_and_clear(tmp_path):
    p = tmp_path / "open_position.json"
    pos = PositionState(symbol="BTCUSDT", qty=0.01, status="OPEN")
    save_position(pos, p)
    loaded = load_position(p)
    assert loaded is not None
    assert loaded.symbol == "BTCUSDT"
    pos.status = "CLOSED"
    clear_position(p)
    assert not p.exists()


def test_broken_json_fallback(tmp_path):
    p = tmp_path / "open_position.json"
    p.write_text("{bad", encoding="utf-8")
    assert load_position(p) is None
