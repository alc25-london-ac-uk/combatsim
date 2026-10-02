import math
import random

from combatant import PlayerCharacter
from data import spawn
from combat import monte_carlo
from policy import Policy
from evaluation import build_party, POLICIES
from policy_greedyutility import GreedyUtilityPolicy

XP_THRESHOLDS_BY_LEVEL: dict[int, dict[str, int]] = {
    1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
    2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
    3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
    4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
    5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
}

XP_BY_CR: dict[float, int] = {
    0: 10, 0.125: 25, 0.25: 50, 0.5: 100,
    1: 200, 2: 450, 3: 700, 4: 1100, 5: 1800,
    6: 2300, 7: 2900, 8: 3900, 9: 5000, 10: 5900,
}

TIERS = ["Trivial", "Easy", "Medium", "Hard", "Deadly"]

def encounter_multiplier(monster_count: int) -> float:
    if monster_count <= 1:
        return 1.0
    if monster_count == 2:
        return 1.5
    if monster_count <= 6:
        return 2.0
    if monster_count <= 10:
        return 2.5
    if monster_count <= 14:
        return 3.0
    return 4.0

def classify_difficulty(monster_names: list[str], monster_registry: dict, party: list[PlayerCharacter]) -> str:
    total_xp = sum(XP_BY_CR[monster_registry[name].challenge_rating] for name in monster_names)
    adjusted_xp = total_xp * encounter_multiplier(len(monster_names))

    party_thresholds = {
        tier: sum(XP_THRESHOLDS_BY_LEVEL[p.level][tier] for p in party)
        for tier in ("easy", "medium", "hard", "deadly")
    }

    if adjusted_xp >= party_thresholds["deadly"]:
        return "Deadly"
    if adjusted_xp >= party_thresholds["hard"]:
        return "Hard"
    if adjusted_xp >= party_thresholds["medium"]:
        return "Medium"
    if adjusted_xp >= party_thresholds["easy"]:
        return "Easy"
    return "Trivial"

def generate_random_encounter(monster_registry: dict, rng: random.Random, min_monsters: int = 1, max_monsters: int = 8) -> list[str]:
    count = rng.randint(min_monsters, max_monsters)
    names = list(monster_registry.keys())
    return [rng.choice(names) for _ in range(count)]

def run_cr_calibration(player_registry: dict, monster_registry: dict, policy_class: type[Policy], n_encounters: int = 50, trials_per_encounter: int = 200, seed: int = None) -> dict[str, dict]:
    rng = random.Random(seed)
    policy = policy_class()
    by_tier: dict[str, list[dict]] = {tier: [] for tier in TIERS}

    for _ in range(n_encounters):
        party = build_party(player_registry)
        monster_names = generate_random_encounter(monster_registry, rng)
        tier = classify_difficulty(monster_names, monster_registry, party)

        enemies = [
            spawn(monster_registry, name, f"{name} {i + 1}", policy = policy)
            for i, name in enumerate(monster_names)
        ]

        result = monte_carlo(party, enemies, trials_per_encounter, False)
        by_tier[tier].append(result)

    aggregated: dict[str, dict] = {}
    for tier, results in by_tier.items():
        if not results:
            aggregated[tier] = {"n_encounters": 0, "avg_party_win_pct": None, "avg_rounds": None}
            continue
        aggregated[tier] = {
            "n_encounters": len(results),
            "avg_party_win_pct": sum(r["party_win_pct"] for r in results) / len(results),
            "avg_rounds": sum(r["average_rounds"] for r in results) / len(results),
        }

    return aggregated

def print_cr_calibration(policy_name: str, results: dict[str, dict]) -> None:
    print(policy_name)
    header = f"  {'Tier':<10}{'Encounters':>12}{'Avg party win%':>18}{'Avg rounds':>12}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for tier in TIERS:
        r = results[tier]
        if r["n_encounters"] == 0:
            print(f"  {tier:<10}{0:>12}{'--':>18}{'--':>12}")
        else:
            print(f"  {tier:<10}{r['n_encounters']:>12}{r['avg_party_win_pct']:>17.1f}%{r['avg_rounds']:>12.1f}")

def has_damage_modifiers(monster_names: list[str], monster_registry: dict) -> bool:
    return any(
        monster_registry[name].damage_resistances or monster_registry[name].damage_immunities or monster_registry[name].damage_vulnerabilities
        for name in monster_names
    )

def run_policy_sweep(player_registry: dict, monster_registry: dict, n_encounters: int = 100, trials_per_encounter: int = 200, seed: int = None, policy_side: str = "pcs") -> list[dict]:
    rng = random.Random(seed)
    if seed is not None:
        random.seed(seed)

    records = []
    for _ in range(n_encounters):
        monster_names = generate_random_encounter(monster_registry, rng)
        tier = classify_difficulty(monster_names, monster_registry, build_party(player_registry))

        win_pct = {}
        for policy_name, policy_class in POLICIES.items():
            if policy_side == "pcs":
                party = build_party(player_registry, policy_class())
                monster_policy = GreedyUtilityPolicy()
            else:
                party = build_party(player_registry)
                monster_policy = policy_class()
            enemies = [
                spawn(monster_registry, name, f"{name} {i + 1}", policy = monster_policy)
                for i, name in enumerate(monster_names)
            ]
            result = monte_carlo(party, enemies, trials_per_encounter, False)
            win_pct[policy_name] = result["party_win_pct"] if policy_side == "pcs" else result["enemy_win_pct"]

        records.append({
            "monsters": monster_names,
            "tier": tier,
            "has_modifiers": has_damage_modifiers(monster_names, monster_registry),
            "has_casters": any(monster_registry[name].spells for name in monster_names),
            "win_pct": win_pct,
        })

    return records

def summarise_sweep(records: list[dict], baseline: str = "Greedy") -> dict[str, dict]:
    summary = {}
    for policy_name in POLICIES:
        wins = [r["win_pct"][policy_name] for r in records]
        diffs = [r["win_pct"][policy_name] - r["win_pct"][baseline] for r in records]
        n = len(records)
        mean_diff = sum(diffs) / n if n else 0.0
        if n > 1:
            variance = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
            standard_error = math.sqrt(variance / n)
        else:
            standard_error = 0.0
        summary[policy_name] = {
            "n_encounters": n,
            "avg_win_pct": sum(wins) / n if n else None,
            "avg_diff_vs_baseline": mean_diff,
            "diff_standard_error": standard_error,
        }
    return summary

def print_sweep_summary(title: str, records: list[dict]) -> None:
    print(f"{title} ({len(records)} encounters)")
    if not records:
        print("  (none)")
        return
    summary = summarise_sweep(records)
    header = f"  {'Policy':<15}{'Avg win%':>13}{'vs Greedy':>12}{'+/- SE':>9}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name, s in summary.items():
        print(f"  {name:<15}{s['avg_win_pct']:>12.1f}%{s['avg_diff_vs_baseline']:>+11.2f}{s['diff_standard_error']:>9.2f}")

def print_sweep(records: list[dict], policy_side: str = "pcs") -> None:
    print(f"Win% is for the {'PCs' if policy_side == 'pcs' else 'Monsters'} (the side using each policy); the other side is Greedy.")
    print()
    print_sweep_summary("All encounters", records)
    print()
    print_sweep_summary("Encounters with a resistance/immunity/vulnerability", [r for r in records if r["has_modifiers"]])
    print()
    print_sweep_summary("Encounters with no damage modifiers", [r for r in records if not r["has_modifiers"]])
    for tier in TIERS:
        print()
        print_sweep_summary(f"Tier: {tier}", [r for r in records if r["tier"] == tier])

if __name__ == "__main__":
    from data import load_weapons, load_spells, load_players, load_monsters
    from policy_greedyutility import GreedyUtilityPolicy
    from policy_beliefupdating import BeliefUpdatingPolicy

    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    import sys

    if "--sweep" in sys.argv:
        policy_side = "monsters" if "--monsters" in sys.argv else "pcs"
        records = run_policy_sweep(player_registry, monster_registry, n_encounters = 150, trials_per_encounter = 200, seed = 2024, policy_side = policy_side)
        print_sweep(records, policy_side)
    else:
        for name, policy_class in [("Greedy", GreedyUtilityPolicy), ("BeliefUpdating", BeliefUpdatingPolicy)]:
            results = run_cr_calibration(player_registry, monster_registry, policy_class, n_encounters = 50, trials_per_encounter = 200)
            print_cr_calibration(name, results)
            print()
