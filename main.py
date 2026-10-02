from data import load_weapons, load_spells, load_players, load_monsters
from evaluation import run_baseline_comparison, print_comparison

if __name__ == "__main__":
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")
    player_registry = load_players("players.json", weapon_registry, spell_registry)
    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)

    results = run_baseline_comparison(player_registry, monster_registry, n = 10000)
    print_comparison(results)
