import math
from pathlib import Path

import pytest

from actions import Action
from agreement import AgreementStats, measure_agreement
from data import load_weapons, load_spells, load_players, load_monsters
from enums import ActionType
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_omniscient import OmniscientPolicy
from policy_random import RandomPolicy

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

# --- AgreementStats.record ---

def test_identical_actions_count_as_an_exact_match(make_monster, melee_weapon):
    target = make_monster()
    weapon = melee_weapon()
    stats = AgreementStats()

    stats.record("Actor", Action(ActionType.ATTACK, target, weapon = weapon), Action(ActionType.ATTACK, target, weapon = weapon))

    assert (stats.decisions, stats.exact, stats.same_action_type, stats.same_target) == (1, 1, 1, 1)

def test_a_different_weapon_on_the_same_target_is_not_exact_but_matches_type_and_target(make_monster, melee_weapon):
    target = make_monster()
    stats = AgreementStats()

    stats.record("Actor", Action(ActionType.ATTACK, target, weapon = melee_weapon(name = "Sword")), Action(ActionType.ATTACK, target, weapon = melee_weapon(name = "Hammer")))

    assert (stats.exact, stats.same_action_type, stats.same_target) == (0, 1, 1)

def test_a_different_target_is_not_exact_and_not_a_target_match(make_monster, melee_weapon):
    weapon = melee_weapon()
    stats = AgreementStats()

    stats.record("Actor", Action(ActionType.ATTACK, make_monster(name = "A"), weapon = weapon), Action(ActionType.ATTACK, make_monster(name = "B"), weapon = weapon))

    assert (stats.exact, stats.same_action_type, stats.same_target) == (0, 1, 0)

def test_rate_is_zero_when_no_decisions_were_recorded():
    assert AgreementStats().rate(0) == 0.0

def test_agreement_is_tracked_per_combatant(make_monster, melee_weapon):
    target = make_monster()
    weapon = melee_weapon()
    stats = AgreementStats()

    stats.record("Fighter", Action(ActionType.ATTACK, target, weapon = weapon), Action(ActionType.ATTACK, target, weapon = weapon))
    stats.record("Fighter", Action(ActionType.NONE, target), Action(ActionType.ATTACK, target, weapon = weapon))

    assert stats.by_combatant["Fighter"] == [1, 2]

# --- measure_agreement ---

def test_omniscient_agrees_with_itself_on_every_decision(player_registry, monster_registry):
    stats = measure_agreement(player_registry, monster_registry, OmniscientPolicy, "resistant_horde_no_casters", n = 5, seed = 1)

    assert stats.decisions > 0
    assert stats.exact == stats.decisions

def test_random_agrees_with_omniscient_less_often_than_greedy_like_policies(player_registry, monster_registry):
    random_stats = measure_agreement(player_registry, monster_registry, RandomPolicy, "resistant_horde_no_casters", n = 20, seed = 1)
    belief_stats = measure_agreement(player_registry, monster_registry, BeliefUpdatingPolicy, "resistant_horde_no_casters", n = 20, seed = 1)

    assert random_stats.rate(random_stats.exact) < belief_stats.rate(belief_stats.exact)

# --- standard error of the agreement rate ---

def test_standard_error_is_zero_when_every_fight_has_the_same_agreement_rate():
    stats = AgreementStats()
    stats.decisions, stats.exact = 40, 20
    stats.per_fight = [(5, 10)] * 4

    assert stats.exact_standard_error() == 0.0

def test_standard_error_grows_when_agreement_differs_between_fights():
    steady = AgreementStats()
    steady.decisions, steady.exact = 40, 20
    steady.per_fight = [(5, 10)] * 4
    uneven = AgreementStats()
    uneven.decisions, uneven.exact = 40, 20
    uneven.per_fight = [(10, 10), (0, 10), (10, 10), (0, 10)]

    assert uneven.exact_standard_error() > steady.exact_standard_error()

def test_the_fight_based_error_is_wider_than_the_naive_per_decision_error():
    stats = AgreementStats()
    stats.decisions, stats.exact = 400, 200
    stats.per_fight = [(10, 10), (0, 10)] * 20 # decisions within a fight agree or disagree together

    naive = math.sqrt(0.5 * 0.5 / 400)
    assert stats.exact_standard_error() > 3 * naive

def test_standard_error_needs_at_least_two_fights():
    stats = AgreementStats()
    stats.decisions, stats.exact = 10, 5
    stats.per_fight = [(5, 10)]

    assert stats.exact_standard_error() == 0.0

def test_measure_agreement_records_one_entry_per_fight(player_registry, monster_registry):
    stats = measure_agreement(player_registry, monster_registry, BeliefUpdatingPolicy, "mage_and_priest_with_gargoyles", n = 6, seed = 1)

    assert len(stats.per_fight) == 6
    assert sum(d for _, d in stats.per_fight) == stats.decisions
    assert sum(e for e, _ in stats.per_fight) == stats.exact

def test_the_agreement_table_prints_a_standard_error_column(capsys):
    from agreement import print_agreement

    stats = AgreementStats()
    stats.decisions, stats.exact = 400, 200
    stats.per_fight = [(10, 10), (0, 10)] * 20

    print_agreement({"Greedy": stats}, "title")

    assert "+/- SE" in capsys.readouterr().out

# --- all configurations, reproducibility and parallel execution ---

from agreement import measure_all_agreement, agreement_title, print_all_agreement
from scenarios import ENCOUNTERS, POLICIES

def _summary(all_stats):
    return {key: {name: (s.decisions, s.exact, s.same_action_type, s.same_target, s.per_fight, s.by_combatant) for name, s in per_policy.items()}
            for key, per_policy in all_stats.items()}

def test_agreement_statistics_survive_being_sent_between_processes():
    import pickle

    stats = AgreementStats()
    stats.record("Fighter", Action(ActionType.NONE, None), Action(ActionType.NONE, None))
    stats.per_fight.append((1, 1))

    copy = pickle.loads(pickle.dumps(stats))

    assert copy.decisions == 1 and copy.by_combatant == {"Fighter": [1, 1]} and copy.per_fight == [(1, 1)]

def test_measure_all_agreement_covers_every_encounter_side_and_policy(player_registry, monster_registry):
    results = measure_all_agreement(player_registry, monster_registry, n = 1, seed = 3, max_workers = 1)

    assert set(results) == set(ENCOUNTERS)
    assert all(set(per_policy) == set(POLICIES) for per_policy in results.values())

def test_agreement_in_parallel_matches_the_sequential_run(player_registry, monster_registry):
    sequential = measure_all_agreement(player_registry, monster_registry, n = 3, seed = 6, max_workers = 1)
    parallel = measure_all_agreement(player_registry, monster_registry, n = 3, seed = 6, max_workers = 3)

    assert _summary(sequential) == _summary(parallel)

def test_agreement_with_the_same_seed_is_reproducible(player_registry, monster_registry):
    first = measure_all_agreement(player_registry, monster_registry, n = 2, seed = 8, max_workers = 2)
    second = measure_all_agreement(player_registry, monster_registry, n = 2, seed = 8, max_workers = 2)

    assert _summary(first) == _summary(second)

def test_agreement_titles_name_the_encounter_and_the_pc_side():
    title = agreement_title("five_casters_with_undead")

    assert "five_casters_with_undead" in title and "PCs" in title and "Greedy Monsters" in title

def test_print_all_agreement_prints_one_table_per_encounter(player_registry, monster_registry, capsys):
    print_all_agreement(measure_all_agreement(player_registry, monster_registry, n = 1, seed = 1, max_workers = 1))

    output = capsys.readouterr().out
    for encounter in ENCOUNTERS:
        assert output.count(encounter) == 1
