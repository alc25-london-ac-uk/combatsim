from pathlib import Path

import pytest

from data import load_weapons, load_spells, load_players, load_monsters
from scenarios import POLICIES, ENCOUNTERS
from evaluation import (
    run_policy_comparison, run_all_comparisons, comparison_title, print_all_comparisons, print_comparison, win_rate_standard_error,
)

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

ENCOUNTER = "mage_and_priest_with_gargoyles"

def test_run_policy_comparison_returns_one_result_per_policy(player_registry, monster_registry):
    results = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 5)

    assert set(results) == set(POLICIES)
    for result in results.values():
        assert result["party_win_pct"] + result["enemy_win_pct"] + result["draw_pct"] == 100.0
        assert result["average_rounds"] > 0
        assert result["n"] == 5

def test_the_policy_under_test_plays_the_pcs_and_the_monsters_always_play_greedy(player_registry, monster_registry, monkeypatch):
    from policy_random import RandomPolicy
    from policy_greedyutility import GreedyUtilityPolicy
    from policy_beliefupdating import BeliefUpdatingPolicy
    from policy_omniscient import OmniscientPolicy

    seen = []

    def spy(party, enemies, n, log):
        seen.append((type(party[0].ai.policy), {type(e.ai.policy) for e in enemies}))
        return {"party_win_pct": 0.0, "enemy_win_pct": 100.0, "draw_pct": 0.0, "average_rounds": 1.0, "n": n}

    monkeypatch.setattr("evaluation.monte_carlo", spy)

    run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 1)

    assert [pcs for pcs, _ in seen] == [RandomPolicy, GreedyUtilityPolicy, BeliefUpdatingPolicy, OmniscientPolicy]
    assert all(monsters == {GreedyUtilityPolicy} for _, monsters in seen)

def test_run_all_comparisons_covers_every_encounter_and_policy(player_registry, monster_registry):
    all_results = run_all_comparisons(player_registry, monster_registry, n = 2)

    assert set(all_results) == set(ENCOUNTERS)
    assert all(set(results) == set(POLICIES) for results in all_results.values())

def test_comparison_titles_say_which_side_is_tested_and_which_direction_is_better():
    title = comparison_title("resistant_horde_no_casters")

    assert "resistant_horde_no_casters" in title and "PCs" in title and "Greedy Monsters" in title and "higher PC win%" in title

def test_print_all_comparisons_prints_one_table_per_encounter(player_registry, monster_registry, capsys):
    print_all_comparisons(run_all_comparisons(player_registry, monster_registry, n = 2))

    output = capsys.readouterr().out
    for encounter in ENCOUNTERS:
        assert output.count(encounter) == 1
    assert output.count("Omniscient") == 3

# --- standard error of a win rate ---

def test_win_rate_standard_error_matches_the_binomial_formula():
    assert abs(win_rate_standard_error(50.0, 10000) - 0.5) < 1e-9
    assert abs(win_rate_standard_error(50.0, 100) - 5.0) < 1e-9

def test_win_rate_standard_error_is_zero_at_the_extremes_and_when_there_are_no_fights():
    assert win_rate_standard_error(0.0, 1000) == 0.0
    assert win_rate_standard_error(100.0, 1000) == 0.0
    assert win_rate_standard_error(50.0, 0) == 0.0

def test_the_comparison_table_prints_a_standard_error_beside_the_pc_win_rate(capsys):
    results = {"Greedy": {"party_win_pct": 50.0, "enemy_win_pct": 50.0, "draw_pct": 0.0, "average_rounds": 4.0, "n": 10000}}

    print_comparison(results, "title")

    output = capsys.readouterr().out
    assert "+/- SE" in output
    assert "50.0%" in output and "0.5" in output

# --- reproducibility and parallel execution ---

def test_the_same_seed_gives_identical_results(player_registry, monster_registry):
    first = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 20, seed = 5)
    second = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 20, seed = 5)

    assert first == second

def test_different_seeds_give_different_results(player_registry, monster_registry):
    first = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 40, seed = 1)
    second = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 40, seed = 2)

    assert first != second

def test_running_in_parallel_gives_exactly_the_sequential_results(player_registry, monster_registry):
    sequential = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 15, seed = 9, max_workers = 1)
    parallel = run_policy_comparison(player_registry, monster_registry, ENCOUNTER, n = 15, seed = 9, max_workers = 3)

    assert sequential == parallel

def test_all_comparisons_in_parallel_match_the_sequential_run(player_registry, monster_registry):
    sequential = run_all_comparisons(player_registry, monster_registry, n = 3, seed = 4, max_workers = 1)
    parallel = run_all_comparisons(player_registry, monster_registry, n = 3, seed = 4, max_workers = 3)

    assert sequential == parallel

def test_a_single_comparison_reproduces_the_same_cell_of_the_full_run(player_registry, monster_registry):
    everything = run_all_comparisons(player_registry, monster_registry, n = 6, seed = 11, max_workers = 3)
    single = run_policy_comparison(player_registry, monster_registry, "resistant_horde_no_casters", n = 6, seed = 11)

    assert single == everything["resistant_horde_no_casters"]

def test_the_progress_lines_go_to_standard_error_not_into_the_tables(player_registry, monster_registry, capsys):
    run_all_comparisons(player_registry, monster_registry, n = 1, seed = 1, max_workers = 1, progress = True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("jobs finished") == 12
