from combatant import Combatant
from data import spawn, load_weapons, load_spells, load_players, load_monsters
from combat import monte_carlo

if __name__ == "__main__":
    weapon_registry = load_weapons("weapons.json")
    spell_registry = load_spells("spells.json")

    player_registry = load_players("players.json", weapon_registry, spell_registry)
    players: list[Combatant] = [spawn(player_registry, "Fighter"), spawn(player_registry, "Cleric"), spawn(player_registry, "Wizard")]

    monster_registry = load_monsters("monsters.json", weapon_registry, spell_registry)
    monsters = []
    
    for i in range(4):
        monsters.append(spawn(monster_registry, "Goblin", f"Goblin {chr(65 + i)}"))
    for i in range(2):
        monsters.append(spawn(monster_registry, "Hobgoblin", f"Hobgoblin {chr(65 + i)}"))

    results = monte_carlo(players, monsters, 10000, False)

    print(f"Party wins: {results['party_win_pct']:.1f}%")
    print(f"Enemy wins: {results['enemy_win_pct']:.1f}%")
    print(f"Draws:      {results['draw_pct']:.1f}%")
    print(f"Runs:       {results['n']}")