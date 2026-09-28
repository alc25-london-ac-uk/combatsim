import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

def test_simulate_returns_win_rate_percentages_summing_to_100():
    # small n keeps this fast; the real app defaults to 10000
    response = client.get("/simulate", params = {"goblins": 1, "hobgoblins": 0, "n": 20})

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"party_win_pct", "enemy_win_pct", "draw_pct", "n"}
    assert data["n"] == 20
    assert data["party_win_pct"] + data["enemy_win_pct"] + data["draw_pct"] == pytest.approx(100.0)

def test_simulate_live_returns_a_list_of_round_snapshots():
    response = client.get("/simulate-live", params = {"goblins": 1, "hobgoblins": 0})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first_snapshot = data[0]
    assert "log" in first_snapshot
    assert "positions" in first_snapshot

def test_simulate_live_snapshot_positions_include_expected_fields():
    response = client.get("/simulate-live", params = {"goblins": 1, "hobgoblins": 0})
    data = response.json()

    combatant_entry = data[0]["positions"][0]
    assert set(combatant_entry.keys()) == {"name", "team", "hp", "max_hp", "x", "y", "alive"}
