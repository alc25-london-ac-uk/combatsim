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

    assert len(party) == 4
    assert all(isinstance(p.ai.policy, GreedyUtilityPolicy) for p in party)

def test_the_party_is_two_fighters_a_cleric_and_a_wizard_with_distinct_names(player_registry):
    party = build_party(player_registry)

    assert [p.type_name for p in party] == ["Fighter", "Fighter", "Cleric", "Wizard"]
    assert [p.name for p in party] == ["Fighter 1", "Fighter 2", "Cleric", "Wizard"]
    assert all(p.level == 5 for p in party)
    assert party[0] is not party[1] and party[0].weapons is not party[1].weapons # separate copies, not one shared Fighter

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
    names = [e.name for e in build_encounter("priests_with_boars", monster_registry)]

    assert names[:2] == ["Priest 1", "Priest 2"] and "Priest" not in names
    assert "Giant Boar 1" in names and "Giant Boar 7" in names and "Giant Boar" not in names
    assert [e.name for e in build_encounter("resistant_horde_no_casters", monster_registry)].count("Gargoyle") == 1 # a singleton keeps its plain name

def test_spellcasters_are_never_more_than_a_quarter_of_a_named_encounter(monster_registry):
    # so that picking out the dangerous caster from a group of non-casters is a real decision
    for name, monster_names in ENCOUNTERS.items():
        casters = [n for n in monster_names if monster_registry[n].spells]
        assert len(casters) / len(monster_names) <= 0.25, name

def test_level_1_casters_are_not_used_in_the_named_encounters():
    for name, monster_names in ENCOUNTERS.items():
        assert "Acolyte" not in monster_names, name

def test_build_encounter_applies_the_given_policy(monster_registry):
    from scenarios import build_encounter
    policy = BeliefUpdatingPolicy()
    enemies = build_encounter("priests_with_boars", monster_registry, policy)

    assert all(e.ai.policy is policy for e in enemies)

def test_the_named_encounters_cover_the_hidden_variables_they_are_meant_to_test(monster_registry):
    priests = [monster_registry[n] for n in ENCOUNTERS["priests_with_boars"]]
    assert any(any(s.is_healing for s in m.spells) for m in priests) # a healer

    puzzle = [monster_registry[n] for n in ENCOUNTERS["resistant_horde_no_casters"]]
    assert any(m.damage_vulnerabilities for m in puzzle) and any(m.damage_immunities for m in puzzle) and any(m.damage_resistances for m in puzzle)

def test_the_priest_encounter_isolates_the_casters_and_the_horde_isolates_the_defences(monster_registry):
    # the Priests are the only creatures with anything hidden, and the horde has no spellcasters at all
    boars = [monster_registry[n] for n in ENCOUNTERS["priests_with_boars"] if n == "Giant Boar"]
    assert boars and not any(m.spells or m.damage_resistances or m.damage_vulnerabilities or m.damage_immunities for m in boars)

    assert not any(monster_registry[n].spells for n in ENCOUNTERS["resistant_horde_no_casters"])

def test_every_named_encounter_fits_in_the_api_monster_limit():
    from api import MAX_MONSTERS
    for name, monster_names in ENCOUNTERS.items():
        assert len(monster_names) <= MAX_MONSTERS, name

# --- configurations and seeds ---

from scenarios import configurations, configuration_seed

def test_configurations_cover_every_encounter_and_policy_exactly_once():
    configs = configurations()

    assert len(configs) == len(ENCOUNTERS) * len(POLICIES) == 8
    assert len(set(configs)) == len(configs)
    assert set(configs) == {(e, p) for e in ENCOUNTERS for p in POLICIES}

def test_a_missing_base_seed_means_no_seed():
    assert configuration_seed(None, "priests_with_boars", "Greedy") is None

def test_every_configuration_gets_its_own_seed_derived_from_the_base_seed():
    seeds = [configuration_seed(1000, e, p) for e, p in configurations()]

    assert len(set(seeds)) == 8
    assert min(seeds) == 1000 and max(seeds) == 1007

def test_a_configurations_seed_does_not_depend_on_which_other_configurations_run():
    first = configuration_seed(7, "resistant_horde_no_casters", "BeliefUpdating")
    again = configuration_seed(7, "resistant_horde_no_casters", "BeliefUpdating")

    assert first == again
