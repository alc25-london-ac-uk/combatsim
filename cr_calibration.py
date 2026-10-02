import random

from combatant import PlayerCharacter
from data import spawn
from combat import monte_carlo
from policy import Policy
from evaluation import build_party

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

if __name__ == "__main__":
    from data import load_weapons, load_spells, load_players, load_monsters
    from policy_greedyutility import GreedyUtilityPolicy
    from policy_beliefupdating import BeliefUpdatingPolicy

    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    for name, policy_class in [("Greedy", GreedyUtilityPolicy), ("BeliefUpdating", BeliefUpdatingPolicy)]:
        results = run_cr_calibration(player_registry, monster_registry, policy_class, n_encounters = 50, trials_per_encounter = 200)
        print_cr_calibration(name, results)
        print()
