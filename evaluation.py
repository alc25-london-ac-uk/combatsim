from typing import Optional

from combatant import Combatant
from data import spawn, load_weapons, load_spells, load_players, load_monsters
from combat import monte_carlo
from policy import Policy
from policy_random import RandomPolicy
from policy_greedyutility import GreedyUtilityPolicy
from policy_beliefupdating import BeliefUpdatingPolicy
from policy_omniscient import OmniscientPolicy

POLICIES: dict[str, type[Policy]] = {
    "Random": RandomPolicy,
    "Greedy": GreedyUtilityPolicy,
    "BeliefUpdating": BeliefUpdatingPolicy,
    "Omniscient": OmniscientPolicy,
}

def build_party(player_registry: dict, policy: Optional[Policy] = None) -> list[Combatant]:
    return [spawn(player_registry, name, policy = policy) for name in ("Fighter", "Cleric", "Wizard")]

def build_enemies(monster_registry: dict, policy: Policy) -> list[Combatant]:
    monsters = [
        spawn(monster_registry, "Mage", policy = policy),
        spawn(monster_registry, "Priest", policy = policy),
    ]
    for i in range(2):
        monsters.append(spawn(monster_registry, "Magmin", f"Magmin {chr(65 + i)}", policy = policy))
    return monsters

def build_resistant_enemies(monster_registry: dict) -> list[Combatant]:
    names = ["Skeleton"] * 4 + ["Awakened Tree"] * 3 + ["Mummy"] * 2 + ["Magmin"] * 2 + ["Gargoyle"]
    return [spawn(monster_registry, name, f"{name} {i + 1}", policy = GreedyUtilityPolicy()) for i, name in enumerate(names)]

def run_baseline_comparison(player_registry: dict, monster_registry: dict, n: int = 10000) -> dict[str, dict]:
    results = {}
    for name, policy_class in POLICIES.items():
        party = build_party(player_registry)
        enemies = build_enemies(monster_registry, policy_class())
        results[name] = monte_carlo(party, enemies, n, False)
    return results

def run_party_policy_comparison(player_registry: dict, monster_registry: dict, n: int = 10000) -> dict[str, dict]:
    results = {}
    for name, policy_class in POLICIES.items():
        party = build_party(player_registry, policy_class())
        enemies = build_resistant_enemies(monster_registry)
        results[name] = monte_carlo(party, enemies, n, False)
    return results

def print_comparison(results: dict[str, dict], title: str = "") -> None:
    if title:
        print(title)
    header = f"{'Policy':<15}{'Party win%':>12}{'Enemy win%':>12}{'Draw%':>10}{'Avg rounds':>12}"
    print(header)
    print("-" * len(header))
    for name, r in results.items():
        print(f"{name:<15}{r['party_win_pct']:>11.1f}%{r['enemy_win_pct']:>11.1f}%{r['draw_pct']:>9.1f}%{r['average_rounds']:>12.1f}")

if __name__ == "__main__":
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    print_comparison(run_baseline_comparison(player_registry, monster_registry, n = 10000),
                     "Policy on ENEMIES (Mage, Priest, 2 Magmin) vs Greedy party - lower party win% = stronger enemy policy")
    print()
    print_comparison(run_party_policy_comparison(player_registry, monster_registry, n = 10000),
                     "Policy on PARTY vs resistant Greedy enemies (4 Skeleton, 3 Awakened Tree, 2 Mummy, 2 Magmin, Gargoyle) - higher party win% = stronger party policy")