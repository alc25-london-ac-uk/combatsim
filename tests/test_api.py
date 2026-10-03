import json

import pytest
from fastapi.testclient import TestClient

import api
from api import app, MAX_MONSTERS, MAX_RUNS
from scenarios import POLICIES, ENCOUNTERS

client = TestClient(app)

@pytest.fixture(autouse = True)
def run_simulations_in_this_process(monkeypatch):
    monkeypatch.setattr(api, "SIMULATE_WORKERS", 1) # no extra processes in tests

def _simulate(monsters, **extra):
    return client.post("/simulate", json = {"monsters": monsters, **extra})

# --- /health, /monsters, /encounters ---

def test_health_reports_ok():
    assert client.get("/health").json() == {"status": "ok"}

def test_monsters_lists_every_monster_with_the_fields_the_front_end_needs():
    rows = client.get("/monsters").json()

    assert len(rows) == len(api.monster_registry)
    assert all(set(r) == {"name", "cr", "hp", "ac", "vulnerabilities", "resistances", "immunities", "spells", "attacks"} for r in rows)

def test_monsters_are_sorted_by_challenge_rating_then_name():
    rows = client.get("/monsters").json()

    keys = [(r["cr"], r["name"]) for r in rows]
    assert keys == sorted(keys)

def test_monsters_report_resistances_and_spells():
    rows = {r["name"]: r for r in client.get("/monsters").json()}

    assert "bludgeoning" in rows["Skeleton"]["vulnerabilities"] and "poison" in rows["Skeleton"]["immunities"]
    assert "fireball" in [s.lower() for s in rows["Mage"]["spells"]]

def test_encounters_lists_the_three_named_encounters_with_their_monsters():
    rows = client.get("/encounters").json()

    assert [r["id"] for r in rows] == list(ENCOUNTERS)
    for row in rows:
        expanded = sorted(m["name"] for m in row["monsters"] for _ in range(m["count"]))
        assert expanded == sorted(ENCOUNTERS[row["id"]])
        assert row["monster_count"] == len(ENCOUNTERS[row["id"]])
        assert row["cr_tier"] in ("Trivial", "Easy", "Medium", "Hard", "Deadly") and row["adjusted_xp"] > 0

# --- POST /simulate ---

def test_simulate_returns_one_result_per_policy_in_order():
    response = _simulate([{"name": "Goblin", "count": 2}], runs = 10, seed = 1)

    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == 10 and data["monster_count"] == 2
    assert [r["policy"] for r in data["results"]] == list(POLICIES)

def test_simulate_win_rates_sum_to_100_and_report_a_standard_error():
    results = _simulate([{"name": "Goblin", "count": 3}], runs = 20, seed = 2).json()["results"]

    for r in results:
        assert r["pc_win_pct"] + r["monster_win_pct"] + r["draw_pct"] == pytest.approx(100.0)
        assert r["n"] == 20 and r["pc_win_se"] >= 0 and r["average_rounds"] > 0

def test_the_same_seed_gives_the_same_simulation():
    first = _simulate([{"name": "Skeleton", "count": 2}, {"name": "Zombie", "count": 1}], runs = 15, seed = 7).json()
    second = _simulate([{"name": "Skeleton", "count": 2}, {"name": "Zombie", "count": 1}], runs = 15, seed = 7).json()

    assert first == second

def test_repeated_entries_for_the_same_monster_are_added_together():
    split = _simulate([{"name": "Goblin", "count": 1}, {"name": "Goblin", "count": 2}], runs = 3, seed = 4).json()
    together = _simulate([{"name": "Goblin", "count": 3}], runs = 3, seed = 4).json()

    assert split == together

def test_simulate_uses_the_default_run_count_when_none_is_given():
    assert _simulate([{"name": "Goblin", "count": 1}], seed = 1).json()["runs"] == 100

@pytest.mark.parametrize("body,reason", [
    ({"monsters": []}, "no monsters"),
    ({"monsters": [{"name": "Goblin", "count": 0}]}, "a zero count"),
    ({"monsters": [{"name": "Goblin", "count": MAX_MONSTERS + 1}]}, "one entry with too many"),
    ({"monsters": [{"name": "Goblin", "count": MAX_MONSTERS}, {"name": "Skeleton", "count": 1}]}, "too many in total"),
    ({"monsters": [{"name": "Not A Monster", "count": 1}]}, "an unknown monster"),
    ({"monsters": [{"name": "Goblin", "count": 1}], "runs": MAX_RUNS + 1}, "too many runs"),
    ({"monsters": [{"name": "Goblin", "count": 1}], "runs": 0}, "zero runs"),
    ({}, "a missing monster list"),
])
def test_simulate_rejects_invalid_requests(body, reason):
    assert client.post("/simulate", json = body).status_code == 422, reason

def test_the_unknown_monster_error_names_the_monster():
    response = _simulate([{"name": "Not A Monster", "count": 1}])

    assert "Not A Monster" in response.json()["detail"]

# --- POST /simulate-live ---

@pytest.fixture(scope = "module")
def live_fight():
    return TestClient(app).post("/simulate-live", json = {"encounter": "mage_and_priest_with_gargoyles", "seed": 5}).json()

def test_simulate_live_returns_the_encounter_the_seed_and_a_list_of_frames(live_fight):
    assert live_fight["encounter"] == "mage_and_priest_with_gargoyles" and live_fight["seed"] == 5
    assert isinstance(live_fight["frames"], list) and len(live_fight["frames"]) > 1

def test_every_frame_has_a_round_an_actor_a_log_and_positions(live_fight):
    for frame in live_fight["frames"]:
        assert set(frame) == {"round", "actor", "log", "winner", "decisions", "positions"}

def test_a_frame_names_whose_turn_it_logs_and_round_headings_name_nobody(live_fight):
    combatants = {p["name"] for p in live_fight["frames"][0]["positions"]}

    for frame in live_fight["frames"]:
        is_round_heading = frame["log"][0].startswith("--- Round")
        assert (frame["actor"] is None) == is_round_heading
        assert is_round_heading or frame["actor"] in combatants

def test_positions_include_hp_slots_and_effects(live_fight):
    entry = live_fight["frames"][-1]["positions"][0]

    assert set(entry) == {"name", "team", "hp", "max_hp", "x", "y", "alive", "spell_slots", "max_spell_slots", "effects"}

def test_the_last_frame_declares_a_winner_and_earlier_ones_do_not(live_fight):
    frames = live_fight["frames"]

    assert frames[-1]["winner"] in ("party", "enemies", "draw")
    assert all(f["winner"] is None for f in frames[:-1])

def test_decisions_explain_the_candidates_and_the_beliefs(live_fight):
    decisions = [d for f in live_fight["frames"] for d in f["decisions"]]

    assert decisions
    pc_decision = next(d for d in decisions if d["combatant"] in ("Fighter", "Cleric", "Wizard") and d["chosen"] is not None)
    assert pc_decision["candidates"] and any(c["chosen"] for c in pc_decision["candidates"])
    assert pc_decision["beliefs"] and set(pc_decision["beliefs"][0]) >= {"name", "hp", "ac", "saves", "damage_types", "flags"}

def test_a_live_fight_can_be_replayed_from_its_seed(live_fight):
    replay = TestClient(app).post("/simulate-live", json = {"encounter": "mage_and_priest_with_gargoyles", "seed": 5}).json()

    assert replay == live_fight

def test_a_live_fight_without_a_seed_reports_the_seed_it_used():
    first = client.post("/simulate-live", json = {"encounter": "mage_and_priest_with_gargoyles"}).json()
    replay = client.post("/simulate-live", json = {"encounter": "mage_and_priest_with_gargoyles", "seed": first["seed"]}).json()

    assert replay == first

def test_the_live_response_is_plain_json():
    response = client.post("/simulate-live", json = {"encounter": "five_casters_with_undead", "seed": 3})

    assert json.loads(response.text) == response.json()

def test_the_live_fight_puts_beliefupdating_on_the_pcs_and_greedy_on_the_monsters(monkeypatch):
    seen = {}
    real = api.run_combat_live

    def spy(party, enemies, explain = False):
        seen["pcs"] = {type(p.ai.policy) for p in party}
        seen["monsters"] = {type(e.ai.policy) for e in enemies}
        seen["explain"] = explain
        return real(party, enemies, explain)

    monkeypatch.setattr(api, "run_combat_live", spy)
    client.post("/simulate-live", json = {"encounter": "mage_and_priest_with_gargoyles", "seed": 1})

    assert seen == {"pcs": {api.BeliefUpdatingPolicy}, "monsters": {api.GreedyUtilityPolicy}, "explain": True}

def test_an_unknown_encounter_is_not_found():
    assert client.post("/simulate-live", json = {"encounter": "nope"}).status_code == 404

def test_large_responses_are_compressed():
    response = client.post("/simulate-live", json = {"encounter": "five_casters_with_undead", "seed": 3}, headers = {"Accept-Encoding": "gzip"})

    assert response.headers.get("content-encoding") == "gzip"
