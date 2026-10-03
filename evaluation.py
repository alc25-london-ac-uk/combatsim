import argparse
import math
import random
from typing import Optional

from data import load_weapons, load_spells, load_players, load_monsters
from combat import monte_carlo
from parallel import run_jobs_in_parallel, default_worker_count
from policy_greedyutility import GreedyUtilityPolicy
from scenarios import POLICIES, build_party, build_encounter, configurations, configuration_seed

def _run_configuration(job: tuple) -> dict:
    player_registry, monster_registry, encounter, policy_name, n, seed = job
    if seed is not None:
        random.seed(seed)

    party = build_party(player_registry, POLICIES[policy_name]())
    enemies = build_encounter(encounter, monster_registry, GreedyUtilityPolicy())
    return monte_carlo(party, enemies, n, False)

def _jobs(player_registry: dict, monster_registry: dict, keys: list[tuple[str, str]], n: int, seed: Optional[int]) -> list[tuple]:
    return [(player_registry, monster_registry, encounter, policy_name, n, configuration_seed(seed, encounter, policy_name))
            for encounter, policy_name in keys]

def run_policy_comparison(player_registry: dict, monster_registry: dict, encounter: str, n: int = 10000,
                          seed: Optional[int] = None, max_workers: Optional[int] = 1) -> dict[str, dict]:
    """Run every policy as the PCs' policy in a named encounter, against Monsters that always play GreedyUtilityPolicy."""
    keys = [(encounter, policy_name) for policy_name in POLICIES]
    results = run_jobs_in_parallel(_run_configuration, _jobs(player_registry, monster_registry, keys, n, seed), max_workers)
    return dict(zip(POLICIES, results))

def run_all_comparisons(player_registry: dict, monster_registry: dict, n: int = 10000, seed: Optional[int] = None,
                        max_workers: Optional[int] = None, progress: bool = False) -> dict[str, dict[str, dict]]:
    keys = configurations()
    results = run_jobs_in_parallel(_run_configuration, _jobs(player_registry, monster_registry, keys, n, seed), max_workers, progress)

    grouped: dict[str, dict[str, dict]] = {}
    for (encounter, policy_name), result in zip(keys, results):
        grouped.setdefault(encounter, {})[policy_name] = result
    return grouped

def comparison_title(encounter: str) -> str:
    return f"{encounter}: policy on the PCs vs Greedy Monsters (higher PC win% = stronger PC policy)"

def win_rate_standard_error(win_pct: float, n: int) -> float:
    """Standard error, in percentage points, of a win rate estimated from n independent fights."""
    p = win_pct / 100
    return math.sqrt(p * (1 - p) / n) * 100 if n > 0 else 0.0

def print_comparison(results: dict[str, dict], title: str = "") -> None:
    if title:
        print(title)
    header = f"{'Policy':<15}{'PC win%':>10}{'+/- SE':>9}{'Monster win%':>14}{'Draw%':>9}{'Avg rounds':>12}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        se = win_rate_standard_error(r['party_win_pct'], r['n'])
        print(f"{name:<15}{r['party_win_pct']:>9.1f}%{se:>8.1f}{r['enemy_win_pct']:>13.1f}%{r['draw_pct']:>8.1f}%{r['average_rounds']:>12.1f}")

def print_all_comparisons(all_results: dict[str, dict[str, dict]]) -> None:
    for encounter, results in all_results.items():
        print_comparison(results, comparison_title(encounter))
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Compare the four policies as the PCs' policy on every named encounter; the Monsters always play Greedy.")
    parser.add_argument("--fights", type = int, default = 10000, help = "fights per configuration")
    parser.add_argument("--seed", type = int, default = 2024, help = "base random seed; each configuration derives its own")
    parser.add_argument("--workers", type = int, default = None, help = "parallel processes (default: about 70%% of the CPU threads)")
    arguments = parser.parse_args()

    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    workers = arguments.workers or default_worker_count()
    print(f"{len(configurations())} configurations x {arguments.fights} fights, base seed {arguments.seed}, {workers} workers\n")
    print_all_comparisons(run_all_comparisons(player_registry, monster_registry, n = arguments.fights, seed = arguments.seed, max_workers = workers, progress = True))
