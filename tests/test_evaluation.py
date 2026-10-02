from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from evaluation import POLICIES, build_party, build_enemies, build_resistant_enemies, run_baseline_comparison, run_party_policy_comparison
from policy_random import RandomPolicy
from policy_greedyutility import GreedyUtilityPolicy
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_omniscient import OmniscientPolicy

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

def test_policies_covers_all_four_proposal_conditions():
    assert set(POLICIES) == {"Random", "Greedy", "BeliefUpdating", "Omniscient"}
    assert POLICIES["Random"] is RandomPolicy
    assert POLICIES["Greedy"] is GreedyUtilityPolicy
    assert POLICIES["BeliefUpdating"] is BeliefUpdatingPolicy
    assert POLICIES["Omniscient"] is OmniscientPolicy

def test_build_enemies_applies_the_given_policy_to_every_enemy(monster_registry):
    policy = BeliefUpdatingPolicy()
    enemies = build_enemies(monster_registry, policy)

    assert len(enemies) == 4 # mage + priest + 2 magmin (Deadly tier for a level-5 party)
    assert all(e.ai.policy is policy for e in enemies)

def test_build_party_uses_the_default_policy(player_registry):
    party = build_party(player_registry)

    assert len(party) == 3
    assert all(isinstance(p.ai.policy, GreedyUtilityPolicy) for p in party)

def test_run_baseline_comparison_returns_one_result_per_policy(player_registry, monster_registry):
    results = run_baseline_comparison(player_registry, monster_registry, n = 5)

    assert set(results) == set(POLICIES)
    for result in results.values():
        assert result["party_win_pct"] + result["enemy_win_pct"] + result["draw_pct"] == 100.0
        assert result["average_rounds"] > 0
        assert result["n"] == 5

def test_build_party_accepts_a_policy_override(player_registry):
    policy = BeliefUpdatingPolicy()
    party = build_party(player_registry, policy)

    assert all(p.ai.policy is policy for p in party)

def test_build_resistant_enemies_are_greedy_and_have_damage_modifiers(monster_registry):
    enemies = build_resistant_enemies(monster_registry)

    assert len(enemies) == 12
    assert all(isinstance(e.ai.policy, GreedyUtilityPolicy) for e in enemies)
    assert all(e.damage_resistances or e.damage_immunities or e.damage_vulnerabilities for e in enemies)

def test_run_party_policy_comparison_returns_one_result_per_policy(player_registry, monster_registry):
    results = run_party_policy_comparison(player_registry, monster_registry, n = 5)

    assert set(results) == set(POLICIES)
    for result in results.values():
        assert result["party_win_pct"] + result["enemy_win_pct"] + result["draw_pct"] == 100.0
        assert result["n"] == 5

def test_party_fighter_has_weapons_of_different_damage_types(player_registry):
    fighter = build_party(player_registry)[0]

    assert len({w.damage_type for w in fighter.weapons}) >= 2
