import argparse
import math
import random
from typing import Optional
from dataclasses import dataclass, field

from actions import Action
from combat import run_combat
from combatant import Combatant
from data import load_weapons, load_spells, load_players, load_monsters
from enums import ActionType
from parallel import run_jobs_in_parallel, default_worker_count
from scenarios import POLICIES, build_party, build_encounter, configurations, configuration_seed
from policy import Policy
from policy_greedyutility import GreedyUtilityPolicy
from policy_omniscient import OmniscientPolicy

@dataclass
class AgreementStats:
    decisions: int = 0
    exact: int = 0
    same_action_type: int = 0
    same_target: int = 0
    by_combatant: dict[str, list[int]] = field(default_factory = dict)
    per_fight: list[tuple[int, int]] = field(default_factory = list) # (exact matches, decisions) for each fight

    def record(self, combatant_name: str, action: Action, reference: Action) -> None:
        same_type = action.action_type == reference.action_type
        same_target = action.target is reference.target
        same_choice = (
            (action.weapon.name if action.weapon else None) == (reference.weapon.name if reference.weapon else None)
            and (action.spell.name if action.spell else None) == (reference.spell.name if reference.spell else None)
        )
        is_exact = same_type and same_target and same_choice

        self.decisions += 1
        self.exact += is_exact
        self.same_action_type += same_type
        self.same_target += same_target
        counts = self.by_combatant.setdefault(combatant_name, [0, 0])
        counts[0] += is_exact
        counts[1] += 1

    def rate(self, count: int) -> float:
        return count / self.decisions if self.decisions else 0.0

    def exact_standard_error(self) -> float:
        fights = len(self.per_fight)
        if fights < 2 or self.decisions == 0:
            return 0.0

        rate = self.exact / self.decisions
        mean_decisions = self.decisions / fights
        squared_residuals = sum((exact - rate * decisions) ** 2 for exact, decisions in self.per_fight)
        return math.sqrt(squared_residuals / (fights - 1) / fights) / mean_decisions

def make_probe(policy_class: type[Policy], stats: AgreementStats) -> type[Policy]:
    class AgreementProbe(policy_class):
        def decide(self, combatant: Combatant, combat_state, beliefs, bonus_action: bool = False) -> Action:
            action = super().decide(combatant, combat_state, beliefs, bonus_action)
            reference = OmniscientPolicy().decide(combatant, combat_state, beliefs, bonus_action)
            stats.record(combatant.name, action, reference)
            return action

    return AgreementProbe

def measure_agreement(player_registry: dict, monster_registry: dict, policy_class: type[Policy], encounter: str, n: int = 1000, seed: int = None) -> AgreementStats:
    if seed is not None:
        random.seed(seed)

    stats = AgreementStats()
    party = build_party(player_registry, make_probe(policy_class, stats)())
    enemies = build_encounter(encounter, monster_registry, GreedyUtilityPolicy())

    for _ in range(n):
        decisions_before, exact_before = stats.decisions, stats.exact
        run_combat(party, enemies)
        stats.per_fight.append((stats.exact - exact_before, stats.decisions - decisions_before))

    return stats

def _measure_configuration(job: tuple) -> AgreementStats:
    player_registry, monster_registry, encounter, policy_name, n, seed = job
    return measure_agreement(player_registry, monster_registry, POLICIES[policy_name], encounter, n, seed)

def measure_all_agreement(player_registry: dict, monster_registry: dict, n: int = 1000, seed: Optional[int] = None,
                          max_workers: Optional[int] = None, progress: bool = False) -> dict[str, dict[str, AgreementStats]]:
    keys = configurations()
    jobs = [(player_registry, monster_registry, encounter, policy_name, n, configuration_seed(seed, encounter, policy_name))
            for encounter, policy_name in keys]
    results = run_jobs_in_parallel(_measure_configuration, jobs, max_workers, progress)

    grouped: dict[str, dict[str, AgreementStats]] = {}
    for (encounter, policy_name), stats in zip(keys, results):
        grouped.setdefault(encounter, {})[policy_name] = stats
    return grouped

def print_agreement(results: dict[str, AgreementStats], title: str) -> None:
    print(title)
    header = f"  {'Policy':<15}{'Decisions':>11}{'Exact':>9}{'+/- SE':>8}{'Same type':>11}{'Same target':>13}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name, stats in results.items():
        print(f"  {name:<15}{stats.decisions:>11}{stats.rate(stats.exact) * 100:>8.1f}%{stats.exact_standard_error() * 100:>7.1f}{stats.rate(stats.same_action_type) * 100:>10.1f}%{stats.rate(stats.same_target) * 100:>12.1f}%")

def agreement_title(encounter: str) -> str:
    return f"{encounter}: policy on the PCs vs Greedy Monsters"

def print_all_agreement(all_results: dict[str, dict[str, AgreementStats]]) -> None:
    for encounter, results in all_results.items():
        print_agreement(results, agreement_title(encounter))
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Measure how often each policy picks the same action as Omniscient, as the PCs' policy on every named encounter; the Monsters always play Greedy.")
    parser.add_argument("--fights", type = int, default = 1000, help = "fights per configuration")
    parser.add_argument("--seed", type = int, default = 2024, help = "base random seed; each configuration derives its own")
    parser.add_argument("--workers", type = int, default = None, help = "parallel processes (default: about 70%% of the CPU threads)")
    arguments = parser.parse_args()

    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    workers = arguments.workers or default_worker_count()
    print(f"{len(configurations())} configurations x {arguments.fights} fights, base seed {arguments.seed}, {workers} workers\n")
    print_all_agreement(measure_all_agreement(player_registry, monster_registry, n = arguments.fights, seed = arguments.seed, max_workers = workers, progress = True))
