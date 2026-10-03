from combatant import PlayerCharacter
from data import load_weapons, load_spells, load_players, load_monsters
from scenarios import ENCOUNTERS, build_party

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

def adjusted_encounter_xp(monster_names: list[str], monster_registry: dict) -> float:
    total_xp = sum(XP_BY_CR[monster_registry[name].challenge_rating] for name in monster_names)
    return total_xp * encounter_multiplier(len(monster_names))

def party_thresholds(party: list[PlayerCharacter]) -> dict[str, int]:
    return {
        tier: sum(XP_THRESHOLDS_BY_LEVEL[p.level][tier] for p in party)
        for tier in ("easy", "medium", "hard", "deadly")
    }

def classify_difficulty(monster_names: list[str], monster_registry: dict, party: list[PlayerCharacter]) -> str:
    adjusted_xp = adjusted_encounter_xp(monster_names, monster_registry)
    thresholds = party_thresholds(party)

    if adjusted_xp >= thresholds["deadly"]:
        return "Deadly"
    if adjusted_xp >= thresholds["hard"]:
        return "Hard"
    if adjusted_xp >= thresholds["medium"]:
        return "Medium"
    if adjusted_xp >= thresholds["easy"]:
        return "Easy"
    return "Trivial"

def print_named_encounter_difficulty(monster_registry: dict, party: list[PlayerCharacter]) -> None:
    thresholds = party_thresholds(party)
    print(f"Party thresholds (adjusted XP): {thresholds}\n")
    header = f"{'Encounter':<34}{'Monsters':>9}{'Adjusted XP':>13}{'x Deadly':>10}  Tier"
    print(header)
    print("-" * len(header))
    for name, monster_names in ENCOUNTERS.items():
        adjusted_xp = adjusted_encounter_xp(monster_names, monster_registry)
        print(f"{name:<34}{len(monster_names):>9}{adjusted_xp:>13.0f}{adjusted_xp / thresholds['deadly']:>10.1f}  {classify_difficulty(monster_names, monster_registry, party)}")

if __name__ == "__main__":
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    print_named_encounter_difficulty(monster_registry, build_party(player_registry))
