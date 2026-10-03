from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from scenarios import POLICIES, ENCOUNTERS, build_party, build_encounter
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

def test_build_party_uses_the_default_policy(player_registry):
    party = build_party(player_registry)

    assert len(party) == 3
    assert all(isinstance(p.ai.policy, GreedyUtilityPolicy) for p in party)

def test_build_party_accepts_a_policy_override(player_registry):
    policy = BeliefUpdatingPolicy()
    party = build_party(player_registry, policy)

    assert all(p.ai.policy is policy for p in party)

def test_party_fighter_has_weapons_of_different_damage_types(player_registry):
    fighter = build_party(player_registry)[0]

    assert len({w.damage_type for w in fighter.weapons}) >= 2

def test_every_named_encounter_builds_from_known_monsters(monster_registry):
    for name, monster_names in ENCOUNTERS.items():
        enemies = build_encounter(name, monster_registry)
        assert [e.type_name for e in enemies] == monster_names

def test_build_encounter_labels_duplicates_but_not_singletons(monster_registry):
    names = [e.name for e in build_encounter("five_casters_with_undead", monster_registry)]

    assert "Priest" in names and "Cult Fanatic" in names and "Wight" in names
    assert "Acolyte 1" in names and "Acolyte 2" in names and "Acolyte" not in names

def test_build_encounter_applies_the_given_policy(monster_registry):
    from scenarios import build_encounter
    policy = BeliefUpdatingPolicy()
    enemies = build_encounter("mage_and_priest_with_gargoyles", monster_registry, policy)

    assert all(e.ai.policy is policy for e in enemies)

def test_the_named_encounters_cover_the_hidden_variables_they_are_meant_to_test(monster_registry):
    cult = [monster_registry[n] for n in ENCOUNTERS["five_casters_with_undead"]]
    assert any(any(s.is_healing for s in m.spells) for m in cult) # a healer
    assert any(any(s.concentration for s in m.spells) for m in cult) # a concentration caster

    puzzle = [monster_registry[n] for n in ENCOUNTERS["resistant_horde_no_casters"]]
    assert any(m.damage_vulnerabilities for m in puzzle) and any(m.damage_immunities for m in puzzle)

    mixed = [monster_registry[n] for n in ENCOUNTERS["mage_and_priest_with_gargoyles"]]
    assert any(m.spells for m in mixed) and any(m.damage_resistances for m in mixed)

# --- configurations and seeds ---

from scenarios import configurations, configuration_seed

def test_configurations_cover_every_encounter_and_policy_exactly_once():
    configs = configurations()

    assert len(configs) == len(ENCOUNTERS) * len(POLICIES) == 12
    assert len(set(configs)) == len(configs)
    assert set(configs) == {(e, p) for e in ENCOUNTERS for p in POLICIES}

def test_a_missing_base_seed_means_no_seed():
    assert configuration_seed(None, "mage_and_priest_with_gargoyles", "Greedy") is None

def test_every_configuration_gets_its_own_seed_derived_from_the_base_seed():
    seeds = [configuration_seed(1000, e, p) for e, p in configurations()]

    assert len(set(seeds)) == 12
    assert min(seeds) == 1000 and max(seeds) == 1011

def test_a_configurations_seed_does_not_depend_on_which_other_configurations_run():
    first = configuration_seed(7, "resistant_horde_no_casters", "BeliefUpdating")
    again = configuration_seed(7, "resistant_horde_no_casters", "BeliefUpdating")

    assert first == again
