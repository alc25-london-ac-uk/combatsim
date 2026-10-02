from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from evaluation import POLICIES, build_party, build_enemies, run_baseline_comparison
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

    assert len(enemies) == 6 # 4 goblins + 2 hobgoblins
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
