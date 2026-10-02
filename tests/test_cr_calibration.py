from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from evaluation import build_party
from cr_calibration import (
    XP_BY_CR, XP_THRESHOLDS_BY_LEVEL, TIERS,
    encounter_multiplier, classify_difficulty, generate_random_encounter, run_cr_calibration,
    has_damage_modifiers, run_policy_sweep, summarise_sweep,
)
from policy_greedyutility import GreedyUtilityPolicy
from evaluation import POLICIES

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def weapon_registry():
    return load_weapons(str(REPO_ROOT / "weapons.json"))

@pytest.fixture
def spell_registry():
    return load_spells(str(REPO_ROOT / "spells.json"))

@pytest.fixture
def monster_registry(weapon_registry, spell_registry):
    return load_monsters(str(REPO_ROOT / "monsters.json"), weapon_registry, spell_registry)

@pytest.fixture
def player_registry(weapon_registry, spell_registry):
    return load_players(str(REPO_ROOT / "players.json"), weapon_registry, spell_registry)

# --- encounter_multiplier ---

def test_encounter_multiplier_matches_the_dmg_table():
    assert encounter_multiplier(1) == 1.0
    assert encounter_multiplier(2) == 1.5
    assert encounter_multiplier(3) == 2.0
    assert encounter_multiplier(6) == 2.0
    assert encounter_multiplier(7) == 2.5
    assert encounter_multiplier(10) == 2.5
    assert encounter_multiplier(11) == 3.0
    assert encounter_multiplier(14) == 3.0
    assert encounter_multiplier(15) == 4.0
    assert encounter_multiplier(20) == 4.0

# --- classify_difficulty ---

def test_classify_difficulty_trivial_below_easy_threshold(player_registry, monster_registry):
    party = build_party(player_registry) # 3 level-5 PCs, easy threshold = 750 total
    tier = classify_difficulty(["Goblin"], monster_registry, party) # CR 1/4 = 50 XP, x1 = 50

    assert tier == "Trivial"

def test_classify_difficulty_deadly_above_deadly_threshold(player_registry, monster_registry):
    party = build_party(player_registry) # deadly threshold = 3 * 1100 = 3300
    # 6 monsters at CR >= 2 (>= 450 XP each) = >= 2700 total, x2 multiplier = >= 5400 adjusted
    cr2_plus = next(name for name, m in monster_registry.items() if m.challenge_rating >= 2)
    tier = classify_difficulty([cr2_plus] * 6, monster_registry, party)

    assert tier == "Deadly"

def test_classify_difficulty_respects_party_level(player_registry, monster_registry):
    # same monsters, a lower-level party should see it as relatively harder
    low_level_party = build_party(player_registry)
    for p in low_level_party:
        p.level = 1

    high_level_party = build_party(player_registry)
    for p in high_level_party:
        p.level = 5

    goblin_squad = ["Goblin", "Goblin", "Goblin"]
    low_level_tier = classify_difficulty(goblin_squad, monster_registry, low_level_party)
    high_level_tier = classify_difficulty(goblin_squad, monster_registry, high_level_party)

    assert TIERS.index(low_level_tier) >= TIERS.index(high_level_tier)

# --- generate_random_encounter ---

def test_generate_random_encounter_only_uses_known_monster_names(monster_registry):
    import random
    rng = random.Random(0)

    for _ in range(20):
        encounter = generate_random_encounter(monster_registry, rng)
        assert 1 <= len(encounter) <= 8
        assert all(name in monster_registry for name in encounter)

def test_generate_random_encounter_is_reproducible_with_a_seeded_rng(monster_registry):
    import random

    first = generate_random_encounter(monster_registry, random.Random(123))
    second = generate_random_encounter(monster_registry, random.Random(123))

    assert first == second

# --- run_cr_calibration ---

def test_run_cr_calibration_covers_every_tier_key(player_registry, monster_registry):
    results = run_cr_calibration(player_registry, monster_registry, GreedyUtilityPolicy, n_encounters = 10, trials_per_encounter = 5, seed = 1)

    assert set(results) == set(TIERS)
    assert sum(r["n_encounters"] for r in results.values()) == 10

def test_run_cr_calibration_reports_none_for_an_empty_tier(player_registry, monster_registry):
    results = run_cr_calibration(player_registry, monster_registry, GreedyUtilityPolicy, n_encounters = 3, trials_per_encounter = 5, seed = 1)

    for tier, r in results.items():
        if r["n_encounters"] == 0:
            assert r["avg_party_win_pct"] is None
            assert r["avg_rounds"] is None

# --- policy sweep ---

def test_has_damage_modifiers_detects_resistances_and_ignores_plain_monsters(monster_registry):
    assert has_damage_modifiers(["Skeleton"], monster_registry) is True
    assert has_damage_modifiers(["Goblin", "Skeleton"], monster_registry) is True
    assert has_damage_modifiers(["Goblin", "Goblin"], monster_registry) is False

def test_run_policy_sweep_records_every_policy_for_every_encounter(player_registry, monster_registry):
    records = run_policy_sweep(player_registry, monster_registry, n_encounters = 3, trials_per_encounter = 3, seed = 1)

    assert len(records) == 3
    for record in records:
        assert set(record["win_pct"]) == set(POLICIES)
        assert record["tier"] in TIERS
        assert all(0 <= pct <= 100 for pct in record["win_pct"].values())

def test_run_policy_sweep_uses_the_same_encounters_for_the_same_seed(player_registry, monster_registry):
    first = run_policy_sweep(player_registry, monster_registry, n_encounters = 4, trials_per_encounter = 2, seed = 5)
    second = run_policy_sweep(player_registry, monster_registry, n_encounters = 4, trials_per_encounter = 2, seed = 5)

    assert [r["monsters"] for r in first] == [r["monsters"] for r in second]

def test_summarise_sweep_computes_paired_differences_against_the_baseline():
    records = [
        {"monsters": [], "tier": "Hard", "has_modifiers": True, "win_pct": {"Random": 0, "Greedy": 50, "BeliefUpdating": 60, "Omniscient": 70}},
        {"monsters": [], "tier": "Hard", "has_modifiers": True, "win_pct": {"Random": 0, "Greedy": 40, "BeliefUpdating": 50, "Omniscient": 80}},
    ]

    summary = summarise_sweep(records)

    assert summary["Greedy"]["avg_diff_vs_baseline"] == 0
    assert summary["BeliefUpdating"]["avg_diff_vs_baseline"] == 10
    assert summary["BeliefUpdating"]["diff_standard_error"] == 0 # identical +10 in both encounters
    assert summary["Omniscient"]["avg_win_pct"] == 75

def test_run_policy_sweep_supports_putting_the_policy_on_the_monsters(player_registry, monster_registry):
    records = run_policy_sweep(player_registry, monster_registry, n_encounters = 2, trials_per_encounter = 3, seed = 1, policy_side = "monsters")

    assert len(records) == 2
    for record in records:
        assert set(record["win_pct"]) == set(POLICIES)
        assert isinstance(record["has_casters"], bool)
